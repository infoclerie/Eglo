"""Pazaryeri / e-ticaret sağlayıcılarının ortak yardımcıları (ürün eşleştirme, KDV dönüşümü, sipariş içe alma, stok listesi)."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def excl(price_incl, vat_rate):
    """KDV dahil fiyat → KDV hariç."""
    return (Decimal(str(price_incl)) / (1 + Decimal(str(vat_rate or 0)) / 100)).quantize(Decimal("0.0001"))


def incl(price_excl, vat_rate):
    """KDV hariç fiyat → KDV dahil (2 hane)."""
    return (Decimal(str(price_excl)) * (1 + Decimal(str(vat_rate or 0)) / 100)).quantize(CENT, rounding=ROUND_HALF_UP)


def product_for(account, *codes):
    """Eşleştirme tablosu (pazaryeri barkodu/SKU) → ürün barkodu/SKU/koli barkodu sırasıyla ürün bulur."""
    from apps.catalog.services import find_product
    codes = [str(c).strip() for c in codes if c not in (None, "")]
    for c in codes:
        l = account.listings.select_related("product").filter(external_barcode=c).first()
        if l:
            return l.product
    for c in codes:
        p, _ = find_product(c)
        if p:
            return p
    return None


def ensure_channel(code, name):
    from apps.catalog.models import SalesChannel
    return SalesChannel.objects.get_or_create(code=code, defaults={"name": name})[0]


def save_order(account, channel_code, external_id, items, raw, status="", **fields):
    """
    Siparişi merkezi havuza alır ve ExternalOrder kaydı açar.
    items: [{"code", "quantity", "unit_price"(KDV hariç)}]. Döner: (sipariş, yeni_mi, uyarı|None)
    """
    from django.core.exceptions import ValidationError

    from apps.sales.services import confirm, import_channel_order

    from ..models import ExternalOrder
    order, new = import_channel_order(channel_code, external_id, items, auto_confirm=False, **fields)
    ExternalOrder.objects.get_or_create(account=account, external_id=external_id,
                                        defaults={"order": order, "status": status, "raw": raw})
    warning = None
    if new and account.config.get("auto_confirm"):
        try:
            confirm(order)
        except ValidationError as exc:  # stok yetersiz: sipariş "Yeni" kalır, havuzda görünür
            warning = f"{order.number}: {' '.join(exc.messages)}"
    return order, new, warning


def stock_rows(account, channel_code):
    """Gönderilecek stok/fiyat satırları: [(ürün, pazaryeri kodu|None, satılabilir adet, KDV hariç kanal fiyatı)]"""
    from apps.catalog.models import Product, SalesChannel
    from apps.inventory.services import stock_summary
    channel = SalesChannel.objects.filter(code=channel_code).first()
    buffer = int(account.config.get("stock_buffer") or 0)
    listings = {l.product_id: l for l in account.listings.all()}
    rows = []
    for p in Product.objects.filter(active=True).exclude(kind__in=["raw", "packaging"]):
        l = listings.get(p.pk)
        if l and not l.sync_stock:
            continue
        qty = max(int(stock_summary(p)["available"]) - buffer, 0)
        price = p.price_for(channel) if channel else p.list_price
        rows.append((p, (l.external_barcode or None) if l else None, qty, price))
    return rows
