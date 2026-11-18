"""
Satın alma iş kuralları (müşteri dokümanı §5, §4.4).
- Öneriler (`create_suggested_requests`) talep oluşturur; sipariş ancak yönetici onayıyla geçerli olur.
- Teklif karşılaştırma sırası: birim fiyat ↑, termin ↑, vade ↓ (uzun vade tercih).
- Mal kabul: inventory.receive ile LOT/SKT kaydedilir, ağırlıklı ortalama maliyet güncellenir.
- Siparişten fazla teslim alınamaz (tolerans Sistem ayarı `purchase.over_receipt_pct`, varsayılan 0).
- Kapatırken eksik/fazla teslim tutanağı (ReceiptDiscrepancy) otomatik oluşur.
- Yoldaki miktar = onaylı/iletilmiş/kısmi siparişlerin açık miktarı → stok önerisinde düşülür.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum

from apps.core.approvals import request_approval
from apps.core.events import publish
from apps.core.models import Sequence, Setting
from apps.inventory import services as inventory

from .models import PurchaseOrder, PurchaseOrderLine, PurchaseRequest, ReceiptDiscrepancy, SupplierQuote

ZERO = Decimal("0")


def incoming_quantity(product):
    rows = PurchaseOrderLine.objects.filter(product=product, order__status__in=PurchaseOrder.OPEN).values_list(
        "quantity", "received_quantity")
    return sum((max(q - r, ZERO) for q, r in rows), ZERO)


def create_suggested_requests(products):
    """Satın alma önerisi > 0 olan ürünler için açık talep yoksa talep açar."""
    created = []
    for p in products:
        s = inventory.purchase_suggestion(p)
        if s["suggested_qty"] > 0 and not PurchaseRequest.objects.filter(product=p, status="open").exists():
            created.append(PurchaseRequest.objects.create(
                product=p, quantity=s["suggested_qty"], source="suggestion",
                reason=f"Günlük ort. {s['avg_daily_sales']} × {s['lead_time_days']} gün + güvenlik {s['safety_stock']} "
                       f"− mevcut {s['available']} − yoldaki {s['incoming']}"))
    return created


def compare_quotes(product, request=None):
    qs = SupplierQuote.objects.filter(product=product).select_related("supplier")
    if request is not None:
        qs = qs.filter(request=request)
    return sorted(qs, key=lambda q: (q.unit_price, q.lead_time_days, -q.payment_term_days))


@transaction.atomic
def order_from_quote(quote, quantity, warehouse, user=None):
    po = PurchaseOrder.objects.create(number=Sequence.next("purchase.order", "SAS-"), supplier=quote.supplier,
                                      warehouse=warehouse, payment_term_days=quote.payment_term_days,
                                      currency=quote.currency)
    PurchaseOrderLine.objects.create(order=po, product=quote.product, quantity=Decimal(str(quantity)),
                                     unit_price=quote.unit_price, vat_rate=quote.product.vat_rate, request=quote.request)
    if quote.request_id:
        PurchaseRequest.objects.filter(pk=quote.request_id).update(status="ordered")
    return po


def submit(po, user=None):
    if po.status != "draft":
        raise ValidationError("Sadece taslak sipariş onaya gönderilebilir.")
    if not po.lines.exists():
        raise ValidationError("Siparişte satır yok.")
    po.status = "approval"
    po.save(update_fields=["status", "updated_at"])
    return request_approval("purchase.order_approve", po, f"Satın alma onayı: {po.number} — {po.supplier.name} ({po.total})", user)


def mark_sent(po, user=None):
    if po.status != "approved":
        raise ValidationError("Onaylanmamış sipariş tedarikçiye iletilemez.")
    po.status = "sent"
    po.save(update_fields=["status", "updated_at"])
    publish("purchase.order_sent", order=po, user=user)
    return po


@transaction.atomic
def receive_line(line, quantity, location, lot_no=None, expiry_date=None, production_date=None, user=None,
                 waybill_no=""):
    po = PurchaseOrder.objects.select_for_update().get(pk=line.order_id)
    line = PurchaseOrderLine.objects.select_for_update().get(pk=line.pk)
    if po.status not in PurchaseOrder.OPEN:
        raise ValidationError("Bu sipariş mal kabule açık değil (onaylı olmalı).")
    qty = Decimal(str(quantity))
    tol = Decimal(str(Setting.get("purchase.over_receipt_pct", 0)))
    if line.received_quantity + qty > line.quantity * (1 + tol / 100):
        raise ValidationError(f"{line.product.sku}: sipariş edilenden fazla teslim alınamaz "
                              f"(sipariş {line.quantity}, alınan {line.received_quantity}, gelen {qty}).")
    move = inventory.receive(line.product, qty, location, lot_no=lot_no, expiry_date=expiry_date,
                             production_date=production_date, producer=po.supplier.name,
                             reference=f"{po.number} {waybill_no}".strip(), user=user, unit_cost=line.unit_price)
    PurchaseOrderLine.objects.filter(pk=line.pk).update(received_quantity=F("received_quantity") + qty)
    po.refresh_from_db()
    lines = list(po.lines.all())
    po.status = "received" if all(l.received_quantity >= l.quantity for l in lines) else "partial"
    po.save(update_fields=["status", "updated_at"])
    publish("purchase.goods_received", order=po, line=line, move=move, user=user)
    return move


@transaction.atomic
def close(po, user=None, note=""):
    """Eksik/fazla teslimle siparişi kapatır; farklar için tutanak oluşturur."""
    if po.status not in ("partial", "received", "sent", "approved"):
        raise ValidationError("Bu sipariş kapatılamaz.")
    for l in po.lines.all():
        if l.received_quantity != l.quantity:
            ReceiptDiscrepancy.objects.create(line=l, ordered=l.quantity, received=l.received_quantity, note=note,
                                              kind="short" if l.received_quantity < l.quantity else "over")
    po.status = "closed" if ReceiptDiscrepancy.objects.filter(line__order=po).exists() else "received"
    po.save(update_fields=["status", "updated_at"])
    return po


def supplier_performance(supplier):
    """Tedarikçi performansı: toplam alış, sipariş sayısı, geciken açık sipariş, eksik teslim tutanağı."""
    pos = PurchaseOrder.objects.filter(supplier=supplier).exclude(status__in=["draft", "cancelled"])
    total = sum((p.total for p in pos), ZERO)
    return {"orders": pos.count(), "total": total, "late_open": sum(1 for p in pos if p.is_late),
            "short_deliveries": ReceiptDiscrepancy.objects.filter(line__order__supplier=supplier, kind="short").count()}


def last_prices(product, limit=10):
    return (PurchaseOrderLine.objects.filter(product=product).exclude(order__status__in=["draft", "cancelled"])
            .select_related("order__supplier").order_by("-order__order_date")[:limit])
