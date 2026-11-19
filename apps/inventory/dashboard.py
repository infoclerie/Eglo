from django.urls import reverse
from django.utils import timezone

from . import services
from .models import StockCount


def widgets(request):
    from django.db.models import Sum

    from apps.catalog.models import Product
    from .models import Quant
    active = Product.objects.filter(active=True).exclude(kind__in=["raw", "packaging"])
    in_stock = Quant.objects.filter(quantity__gt=0, location__is_sellable=True).values("product").distinct().count()
    units = Quant.objects.filter(location__is_sellable=True).aggregate(s=Sum("quantity"))["s"] or 0
    low = len(services.low_stock_products())
    lots = list(services.expiring_lots())
    today = timezone.localdate()
    expired = sum(1 for l in lots if l.expiry_date < today)
    return [
        {"title": "Aktif ürün (satılan)", "value": active.count(), "url": reverse("admin:catalog_product_changelist"),
         "level": "ok" if active.exists() else "warning"},
        {"title": "Stokta olan ürün / toplam adet", "value": f"{in_stock} / {int(units):,}".replace(",", "."), "url": reverse("inventory:summary"),
         "level": "ok" if in_stock else "warning"},
        {"title": "Kritik stok seviyesindeki ürün", "value": low, "url": reverse("inventory:summary") + "?low=1",
         "level": "danger" if low else "ok"},
        {"title": "SKT kontrolü gereken LOT", "value": len(lots) - expired, "url": reverse("admin:inventory_lot_changelist"),
         "level": "warning" if len(lots) - expired else "ok"},
        {"title": "SKT'si geçmiş LOT (blokajlı)", "value": expired, "url": reverse("admin:inventory_lot_changelist"),
         "level": "danger" if expired else "ok"},
        {"title": "Onay bekleyen sayım", "value": StockCount.objects.filter(status="submitted").count(),
         "url": reverse("admin:inventory_stockcount_changelist"),
         "level": "warning" if StockCount.objects.filter(status="submitted").exists() else "ok"},
    ]


def charts(request):
    """Stok değeri (maliyet × fiziksel stok) — ürün grubuna göre."""
    from .models import Quant
    from collections import defaultdict
    from decimal import Decimal

    from django.db.models import Sum

    from apps.catalog.models import Product
    groups = defaultdict(Decimal)
    labels = dict(Product.GROUP)
    for p in Product.objects.annotate(q=Sum("quants__quantity")).exclude(q=None):
        groups[labels.get(p.group, p.group)] += (p.q or 0) * p.cost
    return [{"key": "inventory.chart-stok-degeri", "title": "Stok değeri (maliyet, TL)", "type": "bar",
             "labels": list(groups), "data": [float(v) for v in groups.values()],
             "empty": ("Stok var ama ürünlerin maliyeti girilmemiş; değer hesaplanamıyor. Ürün kartında 'Alış / üretim maliyeti' "
                       "alanını doldurun veya Excel › Fiyatlar ile toplu girin.") if Quant.objects.filter(quantity__gt=0).exists() else
                      "Henüz stok girişi yok. Mal Kabul ekranından veya kanal panelindeki 'açılış stoğu' seçeneğiyle stok girin."}]
