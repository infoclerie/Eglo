"""
Bayi portalı iş kuralları (müşteri dokümanı §8.6).
- Fiyat: sales.unit_price(ürün, bayinin fiyat kanalı, bayi) → bayiye özel liste fiyatı ve iskonto, KDV hariç.
- Stok: satışa uygun stok; bayiye "Stokta / Az stok / Tükendi" ve sipariş edilebilir en fazla miktar gösterilir.
- Sipariş: vadeli (cari) sipariş açılır ve onaylanır → stok ayrılır, toplamaya düşer. Kredi limiti aşılırsa sipariş
  "Yeni" kalır ve otomatik yönetici onayı istenir. Minimum sipariş tutarı: Sistem ayarı `portal.min_order_amount`.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.models import Product, SalesChannel
from apps.core.models import Setting
from apps.inventory.services import InsufficientStock, stock_summary
from apps.sales import services as sales
from apps.sales.models import Campaign

ZERO = Decimal("0")


def channel_for(partner):
    return partner.default_channel or SalesChannel.objects.filter(code="bayi").first() or SalesChannel.objects.first()


def stock_label(product, available):
    if available <= 0:
        return "out", "Tükendi"
    if product.min_stock and available <= product.min_stock:
        return "low", "Az stok"
    return "ok", "Stokta"


def catalog(partner, q=""):
    ch = channel_for(partner)
    qs = Product.objects.filter(active=True).exclude(kind__in=["raw", "packaging"]).select_related("brand", "category")
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode=q))
    rows = []
    for p in qs.order_by("category__name", "name"):
        price = sales.unit_price(p, ch, partner)
        avail = stock_summary(p)["available"]
        level, label = stock_label(p, avail)
        rows.append({"p": p, "price": price, "price_vat": (price * (1 + p.vat_rate / 100)).quantize(Decimal("0.01")),
                     "available": int(avail), "level": level, "label": label})
    return rows


def active_campaigns(partner):
    now, ch = timezone.now(), channel_for(partner)
    return [c for c in Campaign.objects.filter(active=True, starts_at__lte=now, ends_at__gte=now).prefetch_related("channels")
            if not c.channels.exists() or ch in c.channels.all()]


def cart_lines(partner, cart):
    ch = channel_for(partner)
    lines, total = [], ZERO
    for pid, qty in cart.items():
        p = Product.objects.filter(pk=pid, active=True).first()
        if p is None or qty <= 0:
            continue
        price = sales.unit_price(p, ch, partner)
        amount = price * qty
        lines.append({"p": p, "qty": qty, "price": price, "amount": amount, "available": int(stock_summary(p)["available"])})
        total += amount
    return lines, total


def place_order(partner, cart, user=None, note=""):
    """Döner: (sipariş, durum) — durum: 'confirmed' | 'credit_approval' | 'stock'"""
    lines, total = cart_lines(partner, cart)
    if not lines:
        raise ValidationError("Sepet boş.")
    min_amount = Decimal(str(Setting.get("portal.min_order_amount", 0)))
    if total < min_amount:
        raise ValidationError(f"Minimum sipariş tutarı {min_amount} TL (KDV hariç). Sepet: {total:.2f} TL.")
    order = sales.create_order(channel_for(partner), [(l["p"], l["qty"]) for l in lines], customer=partner, user=user,
                               payment_method="term", note=("Bayi portalı siparişi. " + note).strip())
    try:
        sales.confirm(order, user)
        return order, "confirmed"
    except sales.CreditLimitExceeded:
        sales.request_credit_override(order, user)
        return order, "credit_approval"
    except InsufficientStock:
        return order, "stock"
