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


# ---------------------------------------------------------------- ürün aktarımı (ikas / Trendyol / Hepsiburada ortak)
def strip_html(text):
    """Pazaryeri açıklamalarındaki HTML'i düz metne çevirir (paragraf ve liste satır sonu olur)."""
    import html
    import re
    t = re.sub(r"(?i)<\s*(br|/p|/li|/h\d|/div)\s*/?>", "\n", text or "")
    t = re.sub(r"(?i)<\s*li[^>]*>", "• ", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l.strip() for l in t.splitlines())).strip()


def fetch_image(product, url, note="", session=None):
    """Görseli adresten indirip ürüne ekler (aynı adres daha önce eklendiyse atlar). Döner: True/False."""
    import requests
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.catalog.services import add_image
    tag = f"Kaynak: {url}"[:150]
    if product.images.filter(note=tag).exists():
        return False
    http = session or requests
    try:
        r = http.get(url, timeout=20, stream=True)
        if r.status_code != 200:
            return False
        data = r.content if hasattr(r, "content") else b""
        if not data or len(data) > 15 * 1024 * 1024:
            return False
        add_image(product, SimpleUploadedFile("gorsel", data), note=tag)
        return True
    except Exception:  # noqa: BLE001 — görsel alınamazsa ürün aktarımı sürer
        return False


def upsert_product(account, channel, item, opts, stats):
    """
    Tek ürünü (varyant) ürün kartına yazar. item: sku, barcode, name, description, brand, category, sale_incl (KDV dahil satış),
    list_incl, cost, vat, active, images [url], stock. opts: update_existing, import_stock + location, import_images.
    SKU (yoksa barkod) eşleşen ürün güncellenir, yoksa oluşturulur; kanal eşleştirmesi (ChannelListing) yazılır.
    """
    from django.db import transaction

    from apps.catalog.models import Brand, Category, Product, ProductPrice
    from apps.inventory import services as inventory

    from ..models import ChannelListing
    sku, barcode = (item.get("sku") or "").strip(), (item.get("barcode") or "").strip()
    if not sku and not barcode:
        stats["problems"].append(f"{item.get('name')}: SKU ve barkod yok")
        return None
    with transaction.atomic():
        p = (Product.objects.filter(sku=sku).first() if sku else None) or (Product.objects.filter(barcode=barcode).first() if barcode else None)
        is_new = p is None
        if is_new:
            p = Product(sku=sku or barcode, vat_rate=Decimal(str(item.get("vat") if item.get("vat") is not None else opts.get("vat_rate") or 20)))
        elif not opts.get("update_existing", True):
            stats["skipped"] += 1
            ChannelListing.objects.update_or_create(account=account, product=p, defaults={"external_barcode": item.get("external") or barcode or sku})
            return p
        p.name = (item.get("name") or p.name or sku)[:200]
        if barcode and (is_new or not p.barcode) and not Product.objects.filter(barcode=barcode).exclude(pk=p.pk).exists():
            p.barcode = barcode
        base = item.get("list_incl") or item.get("sale_incl")
        if base:
            p.list_price = excl(base, p.vat_rate).quantize(CENT)
        if item.get("cost"):
            p.cost = Decimal(str(item["cost"]))
        if item.get("brand"):
            p.brand = Brand.objects.filter(name__iexact=item["brand"]).first() or Brand.objects.create(name=item["brand"])
        if item.get("category"):
            p.category = Category.objects.filter(name__iexact=item["category"]).first() or Category.objects.create(name=item["category"])
        if is_new or not p.description or "<" in (p.description or ""):
            p.description = strip_html(item.get("description"))[:5000]
        if is_new:
            p.active = bool(item.get("active", True))
        p.save()
        if item.get("sale_incl") and channel is not None:
            ProductPrice.objects.update_or_create(product=p, channel=channel, defaults={"price": excl(item["sale_incl"], p.vat_rate).quantize(CENT)})
        ChannelListing.objects.update_or_create(account=account, product=p, defaults={"external_barcode": item.get("external") or barcode or sku})
        stats["created" if is_new else "updated"] += 1
        loc = opts.get("location")
        if loc is not None and not p.is_kit and item.get("stock") and inventory.stock_summary(p)["physical"] == 0:
            inventory.receive(p, Decimal(str(item["stock"])), loc, lot_no=f"{account.provider.upper()}-ACILIS" if p.track_lot else None,
                              reference=f"{account.name} açılış stoğu", move_type="count_adjust")
            stats["opening_stock"] += 1
    if opts.get("import_images", True):
        for url in (item.get("images") or [])[:6]:
            if fetch_image(p, url, session=opts.get("http")):
                stats["photos"] += 1
    return p


def new_stats():
    return {"created": 0, "updated": 0, "skipped": 0, "opening_stock": 0, "photos": 0, "problems": []}


def import_options(account, payload):
    from apps.inventory.models import Location
    return {"update_existing": payload.get("update_existing", True), "import_images": payload.get("import_images", True),
            "vat_rate": payload.get("vat_rate") or 20,
            "location": Location.objects.filter(pk=payload.get("location_id")).first() if payload.get("import_stock") else None}
