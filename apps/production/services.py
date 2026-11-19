"""
Üretim süreçleri. Stok yalnızca inventory.services üzerinden değişir.
Akış: taslak → malzeme ayır (rezervasyon, FEFO) → üretime başla / fasoncuya gönder (sarf: production_consume)
      → üretimi bitir (mamul KARANTİNAYA girer, LOT + SKT) → kalite kontrol: onay → satışa uygun rafa / red → karantinada kalır.
Formüller:
  ihtiyaç = reçete miktarı × (planlanan / parti büyüklüğü) × (1 + fire% / 100)
  birim maliyet = (sarf edilen malzemelerin maliyeti + fason işçilik × üretilen) / üretilen
"""
from decimal import ROUND_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.events import publish
from apps.core.models import Sequence
from apps.inventory import services as inventory
from apps.inventory.models import Location, StockMove

from .models import ProductionOrder

ZERO = Decimal("0")


def requirements(bom, quantity):
    """[(bileşen, gereken miktar)] — fire payı dahil, 3 haneye yukarı yuvarlanır."""
    factor = Decimal(str(quantity)) / (bom.batch_size or 1)
    out = []
    for l in bom.lines.select_related("component"):
        need = (l.quantity * factor * (1 + l.scrap_pct / 100)).quantize(Decimal("0.001"), rounding=ROUND_UP)
        out.append((l.component, need))
    return out


def availability(order):
    """Malzeme ihtiyaç tablosu: [{component, required, available, shortage}]"""
    rows = []
    for comp, need in requirements(order.bom, order.planned_qty):
        avail = inventory.stock_summary(comp, order.warehouse)["available"]
        if order.status in ("confirmed",):
            avail += sum((r["quantity"] for r in inventory.reservations_for(order.number) if r["product"].pk == comp.pk), ZERO)
        rows.append({"component": comp, "required": need, "available": avail, "shortage": max(need - avail, ZERO)})
    return rows


def create_order(bom, quantity, warehouse, kind="internal", subcontractor=None, planned_date=None, lot_no="",
                 subcontract_unit_cost=0, note="", user=None):
    if Decimal(str(quantity)) <= 0:
        raise ValidationError("Üretim miktarı sıfırdan büyük olmalı.")
    if not bom.lines.exists():
        raise ValidationError("Reçetede malzeme yok.")
    if kind == "subcontract" and subcontractor is None:
        raise ValidationError("Fason üretimde fason firma seçilmeli.")
    return ProductionOrder.objects.create(
        number=Sequence.next("production.order", "URT-"), bom=bom, product=bom.product, planned_qty=quantity,
        warehouse=warehouse, kind=kind, subcontractor=subcontractor, planned_date=planned_date, lot_no=lot_no,
        subcontract_unit_cost=subcontract_unit_cost, note=note)


def _check(order, *allowed):
    order.refresh_from_db()
    if order.status not in allowed:
        raise ValidationError(f"Bu işlem '{order.get_status_display()}' durumundaki emirde yapılamaz.")


@transaction.atomic
def confirm(order, user=None):
    """Malzemeleri FEFO ile ayırır. Eksik varsa hiçbir şey ayırmaz ve eksik listesini bildirir."""
    _check(order, "draft")
    short = [f"{r['component'].sku}: {r['shortage']} eksik" for r in availability(order) if r["shortage"] > 0]
    if short:
        raise ValidationError("Malzeme yetersiz — " + "; ".join(short))
    for comp, need in requirements(order.bom, order.planned_qty):
        inventory.reserve(comp, need, order.number, warehouse=order.warehouse, allow_near_expiry=True)
    order.status = "confirmed"
    order.save(update_fields=["status", "updated_at"])
    publish("production.confirmed", order=order, user=user)
    return order


@transaction.atomic
def start(order, user=None):
    """Ayrılan malzemeyi üretime sarf eder (stok düşer). Fason ise malzeme fasoncuya gönderilmiş sayılır."""
    _check(order, "confirmed")
    moves = inventory.ship_reserved(order.number, user=user, destination=inventory.virtual_location("production"),
                                    move_type="production_consume")
    order.material_cost = sum((m.quantity * m.unit_cost for m in moves), ZERO).quantize(Decimal("0.01"))
    order.status = "at_subcontractor" if order.kind == "subcontract" else "in_progress"
    order.save(update_fields=["material_cost", "status", "updated_at"])
    publish("production.started", order=order, user=user)
    return order


@transaction.atomic
def finish(order, produced_qty, user=None, production_date=None):
    """Mamulü KARANTİNA lokasyonuna LOT/SKT ile alır; kalite kontrol bekler."""
    _check(order, "in_progress", "at_subcontractor")
    qty = Decimal(str(produced_qty))
    if qty <= 0:
        raise ValidationError("Üretilen miktar sıfırdan büyük olmalı.")
    prod_date = production_date or timezone.localdate()
    labor = order.subcontract_unit_cost * qty if order.kind == "subcontract" else ZERO
    unit_cost = ((order.material_cost + labor) / qty).quantize(Decimal("0.0001"))
    quarantine = inventory.find_location(order.warehouse, "quarantine")
    lot_no = order.lot_no or order.number
    inventory.receive(order.product, qty, quarantine, lot_no=lot_no, production_date=prod_date,
                      expiry_date=order.expiry_date, producer=str(order.subcontractor or "Eglo Kozmetik"),
                      reference=order.number, user=user, unit_cost=unit_cost, move_type="production_in")
    order.produced_qty, order.unit_cost, order.lot_no, order.production_date = qty, unit_cost, lot_no, prod_date
    order.status = "qc"
    order.save()
    publish("production.finished", order=order, user=user)
    return order


@transaction.atomic
def quality_check(order, passed, note="", user=None, location=None):
    """Kalite onayı: karantinadan satışa uygun rafa transfer. Red: karantinada kalır (iade / imha kararı ayrıca)."""
    _check(order, "qc")
    order.qc_note, order.qc_by = note, user
    if passed:
        quarantine = inventory.find_location(order.warehouse, "quarantine")
        target = location or Location.objects.filter(warehouse=order.warehouse, kind="storage", active=True).order_by("code").first()
        if target is None:
            raise ValidationError("Depoda raf lokasyonu yok.")
        lot = order.product.lots.filter(lot_no=order.lot_no).first()
        inventory.transfer(order.product, order.produced_qty, quarantine, target, lot=lot, reference=order.number,
                           user=user, note="Kalite onayı")
        order.status = "done"
    else:
        if not note:
            raise ValidationError("Red nedeni yazılmalı.")
        order.status = "rejected"
    order.save()
    publish("production.completed" if passed else "production.rejected", order=order, user=user)
    return order


@transaction.atomic
def cancel(order, user=None):
    _check(order, "draft", "confirmed")
    inventory.release(order.number)
    order.status = "cancelled"
    order.save(update_fields=["status", "updated_at"])
    return order


def incoming_quantity(product):
    """Açık üretim emirlerinden gelecek mamul (satın alma önerisi ve stok ekranındaki 'gelecek' için)."""
    return ProductionOrder.objects.filter(product=product, status__in=("confirmed", "in_progress", "at_subcontractor")
                                          ).aggregate(s=Sum("planned_qty"))["s"] or ZERO


def consumed(order):
    """Sarf edilen malzemeler: [(ürün, LOT, miktar)] (izlenebilirlik)."""
    return [(m.product, m.lot, m.quantity) for m in
            StockMove.objects.select_related("product", "lot").filter(reference=order.number, move_type="production_consume")]
