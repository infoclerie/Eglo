"""
Sevkiyat ve iade iş kuralları (müşteri dokümanı §7). Stok yalnızca inventory servisleriyle değişir.
- Toplama listesi rezervasyonlardan, lokasyon koduna göre (rota) oluşturulur.
- Barkod okutmada ürün siparişte yoksa veya fazla okutulursa hata. Koli barkodu = koli içi adet.
- Paketlemede tartılan ağırlık, beklenen ağırlıktan % tolerans (Sistem ayarı `shipping.weight_tolerance_pct`, varsayılan 5)
  fazla saparsa paketleme durdurulur. Beklenen ağırlık = Σ (ürün birim ağırlığı × miktar).
- İade: açılmış/kullanılmış kozmetik ve hasarlı ürün ASLA satılabilir stoğa alınmaz; iade tamamlama yönetici onaylıdır.
"""
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.services import find_product
from apps.core.approvals import request_approval
from apps.core.events import publish
from apps.core.models import Sequence, Setting
from apps.inventory import services as inventory

from .models import ReturnLine, ReturnRequest, Shipment, ShipmentLine

ZERO = Decimal("0")


# ---------------------------------------------------------------- sevkiyat

@transaction.atomic
def create_shipment(order, method="single"):
    rows = inventory.reservations_for(order.number)
    if not rows:
        raise ValidationError(f"{order.number} için rezerve stok yok.")
    sh = Shipment.objects.create(number=Sequence.next("shipping.shipment", "SVK-"), order=order, method=method)
    expected = ZERO
    for r in rows:
        ShipmentLine.objects.create(shipment=sh, product=r["product"], location=r["location"], lot=r["lot"],
                                    quantity=r["quantity"])
        expected += r["product"].weight_kg * r["quantity"]
    sh.expected_weight_kg = expected
    sh.save(update_fields=["expected_weight_kg"])
    publish("shipping.shipment_created", shipment=sh, order=order)
    return sh


def _set(sh, status, event=None, user=None, **extra):
    sh.status = status
    for k, v in extra.items():
        setattr(sh, k, v)
    sh.save()
    if event:
        publish(event, order=sh.order, shipment=sh, user=user)
    return sh


def start_picking(sh, user=None):
    sh.refresh_from_db()
    if sh.status != "waiting":
        raise ValidationError("Toplama zaten başlamış.")
    return _set(sh, "picking", "shipping.picking_started", user, picker=user)


@transaction.atomic
def scan(sh, code, quantity=1, user=None):
    """El terminalinden barkod okutma. Döner: güncellenen satır."""
    sh = Shipment.objects.select_for_update().get(pk=sh.pk)
    if sh.status == "waiting":
        start_picking(sh, user)
    if sh.status != "picking":
        raise ValidationError("Bu sevkiyat toplama aşamasında değil.")
    product, mult = find_product(code)
    if product is None:
        raise ValidationError(f"Barkod tanınmadı: {code}")
    qty = Decimal(str(quantity)) * mult
    lines = [l for l in sh.lines.filter(product=product) if l.remaining > 0]
    if not lines:
        raise ValidationError(f"{product.sku} bu siparişte yok veya tamamı toplandı — YANLIŞ ÜRÜN.")
    if qty > sum(l.remaining for l in lines):
        raise ValidationError(f"{product.sku}: fazla okutma (kalan {sum(l.remaining for l in lines)}).")
    for l in lines:
        take = min(l.remaining, qty)
        l.picked_quantity += take
        l.save(update_fields=["picked_quantity"])
        qty -= take
        if qty <= 0:
            break
    if all(l.remaining <= 0 for l in sh.lines.all()):
        _set(sh, "picked", "shipping.picked", user)
    return lines[0]


@transaction.atomic
def pack(sh, package_count, weight_kg=None, user=None):
    sh = Shipment.objects.select_for_update().get(pk=sh.pk)
    if sh.status != "picked":
        raise ValidationError("Tüm ürünler barkodla toplanmadan paketlenemez.")
    if package_count < 1:
        raise ValidationError("Koli adedi en az 1 olmalı.")
    if weight_kg is not None and sh.expected_weight_kg > 0:
        tol = Decimal(str(Setting.get("shipping.weight_tolerance_pct", 5)))
        diff = abs(Decimal(str(weight_kg)) - sh.expected_weight_kg) / sh.expected_weight_kg * 100
        if diff > tol:
            raise ValidationError(f"Ağırlık uyuşmuyor: beklenen {sh.expected_weight_kg} kg, tartılan {weight_kg} kg "
                                  f"(%{diff:.1f} sapma > %{tol}). Koli içeriğini kontrol edin.")
    return _set(sh, "packed", "shipping.packed", user, package_count=package_count,
                weight_kg=None if weight_kg is None else Decimal(str(weight_kg)))


@transaction.atomic
def ship(sh, carrier, tracking_no="", user=None, vehicle_plate="", driver_name=""):
    """Kargoya / araca teslim: stok burada düşer (rezervasyon tüketilir)."""
    sh = Shipment.objects.select_for_update().get(pk=sh.pk)
    if sh.status != "packed":
        raise ValidationError("Paketlenmemiş sevkiyat gönderilemez.")
    inventory.ship_reserved(sh.order.number, user=user)
    return _set(sh, "shipped", "shipping.shipped", user, carrier=carrier, tracking_no=tracking_no,
                vehicle_plate=vehicle_plate, driver_name=driver_name, shipped_at=timezone.now())


def deliver(sh, received_by="", note="", user=None):
    sh.refresh_from_db()
    if sh.status != "shipped":
        raise ValidationError("Sevk edilmemiş sevkiyat teslim edilemez.")
    return _set(sh, "delivered", "shipping.delivered", user, received_by=received_by, delivery_note=note,
                delivered_at=timezone.now())


def batch_pick_list(shipments):
    """Çoklu / dalga toplama: birden fazla sevkiyatın satırlarını lokasyon + ürün + LOT bazında birleştirir."""
    agg = defaultdict(lambda: ZERO)
    for l in ShipmentLine.objects.filter(shipment__in=shipments).select_related("location", "product", "lot"):
        agg[(l.location.code, l.product.sku, l.lot.lot_no if l.lot else "")] += l.remaining
    return [{"location": k[0], "sku": k[1], "lot": k[2], "quantity": v} for k, v in sorted(agg.items()) if v > 0]


# ---------------------------------------------------------------- iade

@transaction.atomic
def request_return(order, items, reason, user=None, note=""):
    """items: [(ürün, miktar)]"""
    if order.status not in ("shipped", "delivered"):
        raise ValidationError("Sadece sevk edilmiş siparişler iade edilebilir.")
    rr = ReturnRequest.objects.create(number=Sequence.next("shipping.return", "IADE-"), order=order, reason=reason,
                                      note=note)
    rr.return_code = f"R{rr.number.split('-')[-1]}{order.pk}"
    rr.save(update_fields=["return_code"])
    for product, qty in items:
        ReturnLine.objects.create(request=rr, product=product, quantity=Decimal(str(qty)))
    publish("shipping.return_requested", order=order, return_request=rr, user=user)
    return rr


@transaction.atomic
def receive_return(rr, user=None):
    """İade ürün depoya geldi: müşteri → iade kontrol alanı. LOT, siparişle sevk edilen LOT'tan bulunur."""
    if rr.status != "requested":
        raise ValidationError("İade zaten teslim alınmış.")
    loc = inventory.find_location(rr.order.warehouse, "return_check")
    for line in rr.lines.select_related("product"):
        lot = line.lot
        if lot is None and line.product.track_lot:
            shipped = [x for x in inventory.shipped_lots(rr.order.number, line.product) if x[0] is not None]
            if not shipped:
                raise ValidationError(f"{line.product.sku} bu siparişle sevk edilmemiş.")
            lot = shipped[0][0]
            line.lot = lot
            line.save(update_fields=["lot"])
        inventory.receive_customer_return(line.product, line.quantity, loc, lot=lot, reference=rr.number, user=user)
    rr.status = "received"
    rr.save(update_fields=["status", "updated_at"])
    return rr


def target_condition(line):
    """Hijyen kuralı: açılmış/kullanılmış kozmetik → hasarlı; satılabilir yalnızca 'sellable' işaretliyse."""
    if line.condition == "opened":
        return "damaged"
    return line.condition


@transaction.atomic
def inspect_return(rr, conditions, user=None):
    """conditions: {satır_id: 'sellable'|'opened'|'damaged'|'quarantine'} → yönetici onayına gönderir."""
    if rr.status != "received":
        raise ValidationError("İade henüz depoya ulaşmadı.")
    for line in rr.lines.all():
        cond = conditions.get(line.pk)
        if cond not in dict(ReturnLine.CONDITION):
            raise ValidationError(f"{line.product.sku} için ürün durumu seçilmeli.")
        line.condition = cond
        line.save(update_fields=["condition"])
    rr.status = "inspected"
    rr.save(update_fields=["status", "updated_at"])
    return request_approval("shipping.return_accept", rr, f"İade onayı: {rr.number} ({rr.order})", user)


@transaction.atomic
def complete_return(rr, user=None):
    if rr.status != "inspected":
        raise ValidationError("İade kontrol edilmeden tamamlanamaz.")
    wh = rr.order.warehouse
    src = inventory.find_location(wh, "return_check")
    targets = {"sellable": "storage", "damaged": "damaged", "quarantine": "quarantine"}
    for line in rr.lines.select_related("product", "lot"):
        dest = inventory.find_location(wh, targets[target_condition(line)])
        inventory.transfer(line.product, line.quantity, src, dest, lot=line.lot, reference=rr.number, user=user,
                           note=f"İade sınıflandırma: {line.get_condition_display()}")
    rr.status = "completed"
    rr.save(update_fields=["status", "updated_at"])
    publish("shipping.return_completed", order=rr.order, return_request=rr, user=user)
    return rr
