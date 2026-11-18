"""
Sipariş iş kuralları (müşteri dokümanı §6). Formüller:
- Birim fiyat = kanal fiyatı (yoksa liste fiyatı) × (1 − müşteri indirimi %)  [KDV hariç]
- Satır net = miktar × birim fiyat − satır indirimi − sepet indirimi payı
- Sepet indirimi satırlara net tutarları oranında dağıtılır; KDV her satırın kendi oranıyla net üzerinden hesaplanır
- Kargo bedeli KDV'si %20 (Sistem ayarı `sales.shipping_vat_rate`)
- Genel toplam = Σ satır net + kargo + Σ KDV
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.catalog.models import SalesChannel
from apps.catalog.services import find_product
from apps.core.approvals import request_approval
from apps.core.events import publish
from apps.core.models import Sequence, Setting
from apps.inventory import services as inventory
from apps.partners.services import credit_check

from .models import Campaign, OrderStatusLog, SalesOrder, SalesOrderLine

CENT = Decimal("0.01")
ZERO = Decimal("0")


class CreditLimitExceeded(ValidationError):
    pass


def q2(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def unit_price(product, channel, customer=None):
    if customer is not None and customer.default_channel_id:
        channel = customer.default_channel
    price = product.price_for(channel)
    if customer is not None and customer.discount_pct:
        price = price * (1 - Decimal(str(customer.discount_pct)) / 100)
    return q2(price)


def set_status(order, status, user=None, note=""):
    if order.status == status:
        return order
    order.status, order.status_changed_at = status, timezone.now()
    order.save(update_fields=["status", "status_changed_at", "updated_at"])
    OrderStatusLog.objects.create(order=order, status=status, user=user, note=note)
    publish("sales.status_changed", order=order, status=status)
    return order


def create_order(channel, lines, customer=None, user=None, **fields):
    """lines: [(ürün, miktar) veya (ürün, miktar, birim_fiyat)]"""
    with transaction.atomic():
        order = SalesOrder.objects.create(number=Sequence.next("sales.order", "SIP-"), channel=channel,
                                          customer=customer, **fields)
        if customer is not None:
            order.customer_name = order.customer_name or customer.name
            order.phone = order.phone or customer.phone
            order.email = order.email or customer.email
            order.shipping_address = order.shipping_address or customer.shipping_address or customer.address
            order.billing_address = order.billing_address or customer.address
            order.tax_number = order.tax_number or customer.tax_number
            order.save()
        for row in lines:
            product, qty = row[0], row[1]
            SalesOrderLine.objects.create(order=order, product=product, quantity=Decimal(str(qty)),
                                          unit_price=Decimal(str(row[2])) if len(row) > 2 and row[2] is not None else None)
        OrderStatusLog.objects.create(order=order, status=order.status, user=user)
        compute_totals(order)
    return order


# ---------------------------------------------------------------- kampanyalar

def active_campaigns(order, now=None):
    now = now or timezone.now()
    qs = Campaign.objects.filter(active=True, starts_at__lte=now, ends_at__gte=now).filter(
        Q(max_uses=0) | Q(used_count__lt=F("max_uses"))).prefetch_related("channels", "products")
    return [c for c in qs if not c.channels.exists() or order.channel in c.channels.all()]


def _eligible(campaign, product):
    ids = {p.pk for p in campaign.products.all()}
    return not ids or product.pk in ids


def _cap(campaign, value):
    return min(value, campaign.max_discount) if campaign.max_discount > 0 else value


def compute_totals(order, save=True):
    lines = list(order.lines.select_related("product"))
    for l in lines:
        if l.unit_price is None:
            l.unit_price = unit_price(l.product, order.channel, order.customer)
        if l.vat_rate is None:
            l.vat_rate = l.product.vat_rate
        l.discount = ZERO
        l.order_discount_share = ZERO
    subtotal = sum((l.gross for l in lines), ZERO)
    order_discount, applied = ZERO, []
    shipping_fee = order.shipping_fee

    for c in active_campaigns(order):
        if c.kind == "buy_x_pay_y" and c.x > c.y:
            gained = ZERO
            for l in lines:
                if _eligible(c, l.product):
                    free = int(l.quantity // c.x) * (c.x - c.y)
                    d = q2(free * l.unit_price)
                    l.discount += d
                    gained += d
            if gained:
                applied.append(c.name)
        elif c.kind == "nth_item_price" and c.x >= 2:
            gained = ZERO
            for l in lines:
                if _eligible(c, l.product) and l.unit_price > c.amount:
                    d = q2(int(l.quantity // c.x) * (l.unit_price - c.amount))
                    l.discount += d
                    gained += d
            if gained:
                applied.append(c.name)
        elif c.kind == "cart_percent" and subtotal >= c.min_amount and c.percent > 0:
            order_discount += _cap(c, q2(subtotal * c.percent / 100))
            applied.append(c.name)
        elif c.kind == "coupon_percent" and c.coupon_code and order.coupon_code.strip().upper() == c.coupon_code.upper() \
                and subtotal >= c.min_amount:
            order_discount += _cap(c, q2(subtotal * c.percent / 100))
            applied.append(c.name)
        elif c.kind == "free_shipping_over" and subtotal >= c.min_amount:
            shipping_fee = ZERO
            applied.append(c.name)

    # sepet indirimini satırlara dağıt (yuvarlama farkı son satıra)
    base = sum((l.gross - l.discount for l in lines), ZERO)
    order_discount = min(order_discount, base)
    remaining = order_discount
    for i, l in enumerate(lines):
        if i == len(lines) - 1:
            share = remaining
        else:
            share = q2(order_discount * (l.gross - l.discount) / base) if base else ZERO
        l.order_discount_share = share
        remaining -= share
        l.vat_amount = q2(l.net * l.vat_rate / 100)

    ship_vat = q2(shipping_fee * Decimal(str(Setting.get("sales.shipping_vat_rate", 20))) / 100)
    order.subtotal = subtotal
    order.discount_total = sum((l.discount for l in lines), ZERO) + order_discount
    order.shipping_fee = shipping_fee
    order.vat_total = sum((l.vat_amount for l in lines), ZERO) + ship_vat
    order.grand_total = subtotal - order.discount_total + shipping_fee + order.vat_total
    order.applied_campaigns = ", ".join(applied)[:255]
    if save:
        for l in lines:
            l.save(update_fields=["unit_price", "vat_rate", "discount", "order_discount_share", "vat_amount"])
        order.save(update_fields=["subtotal", "discount_total", "shipping_fee", "vat_total", "grand_total",
                                  "applied_campaigns", "updated_at"])
    return order


# ---------------------------------------------------------------- onay / iptal

@transaction.atomic
def confirm(order, user=None):
    """Siparişi onaylar: kredi limiti → stok rezervasyonu (FEFO, anlık, fazla satış engelli) → toplama emri (olayla)."""
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status not in SalesOrder.EDITABLE:
        raise ValidationError(f"{order.number} zaten işlenmiş ({order.get_status_display()}).")
    if not order.lines.exists():
        raise ValidationError("Siparişte ürün yok.")
    compute_totals(order)
    if order.customer and order.payment_method == "term" and not order.credit_approved:
        ok, balance, limit = credit_check(order.customer, order.grand_total)
        if not ok:
            raise CreditLimitExceeded(
                f"Kredi limiti aşılıyor: açık bakiye {balance} + sipariş {order.grand_total} > limit {limit}. "
                "Yönetici onayı isteyin.")
    for line in order.lines.select_related("product"):
        inventory.reserve(line.product, line.quantity, order.number, warehouse=order.warehouse)
    names = [n.strip() for n in order.applied_campaigns.split(",") if n.strip()]
    if names:
        Campaign.objects.filter(name__in=names, active=True).update(used_count=F("used_count") + 1)
    set_status(order, "reserved", user)
    publish("sales.order_confirmed", order=order, user=user)
    return order


def request_credit_override(order, user=None):
    return request_approval("sales.credit_override", order, f"Kredi limiti aşımı: {order.number} ({order.grand_total})", user)


def request_cancel(order, user=None, reason=""):
    order.refresh_from_db()
    if order.status in ("shipped", "delivered", "cancelled", "returned"):
        raise ValidationError("Sevk edilmiş veya kapanmış sipariş iptal edilemez; iade süreci kullanılmalı.")
    if order.status in ("new", "awaiting_payment"):  # henüz stok ayrılmadı → onaysız iptal
        return cancel(order, user, reason)
    return request_approval("sales.cancel", order, f"Sipariş iptali: {order.number}", user, payload={"reason": reason})


@transaction.atomic
def cancel(order, user=None, reason=""):
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status in ("shipped", "delivered", "cancelled", "returned"):
        raise ValidationError("Bu sipariş iptal edilemez.")
    inventory.release(order.number)
    set_status(order, "cancelled", user, reason)
    publish("sales.order_cancelled", order=order, user=user)
    return order


# ---------------------------------------------------------------- kanal siparişi içe alma

@transaction.atomic
def import_channel_order(channel_code, external_ref, items, auto_confirm=True, **fields):
    """
    Pazaryeri / web siparişini içe alır (entegrasyon modülü çağırır).
    items: [{"code": barkod|SKU|koli barkodu, "quantity": .., "unit_price": KDV hariç (isteğe bağlı)}]
    Aynı kanal + kanal sipariş no daha önce alındıysa YENİ KAYIT AÇMAZ, mevcut siparişi döner.
    Döner: (sipariş, yeni_mi)
    """
    channel = SalesChannel.objects.get(code=channel_code)
    existing = SalesOrder.objects.filter(channel=channel, external_ref=external_ref).first()
    if existing:
        return existing, False
    lines = []
    for it in items:
        product, mult = find_product(str(it["code"]))
        if product is None:
            raise ValidationError(f"Ürün eşleşmedi: {it['code']} (SKU/barkod eşleştirmesi gerekli)")
        qty = Decimal(str(it["quantity"])) * mult
        price = it.get("unit_price")
        lines.append((product, qty, (Decimal(str(price)) / mult) if price is not None else None))
    try:
        with transaction.atomic():
            order = create_order(channel, lines, external_ref=external_ref,
                                 payment_method=fields.pop("payment_method", "marketplace"), **fields)
    except IntegrityError:  # aynı anda iki istek geldi
        return SalesOrder.objects.get(channel=channel, external_ref=external_ref), False
    if auto_confirm:
        order = confirm(order)
    return order, True
