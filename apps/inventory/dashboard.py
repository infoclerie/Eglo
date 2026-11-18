from django.urls import reverse
from django.utils import timezone

from . import services
from .models import StockCount


def widgets(request):
    low = len(services.low_stock_products())
    lots = list(services.expiring_lots())
    today = timezone.localdate()
    expired = sum(1 for l in lots if l.expiry_date < today)
    return [
        {"title": "Kritik stok seviyesindeki ürün", "value": low, "url": reverse("inventory:summary") + "?low=1",
         "level": "danger" if low else "ok"},
        {"title": "SKT kontrolü gereken LOT", "value": len(lots) - expired, "url": reverse("admin:inventory_lot_changelist"),
         "level": "warning" if len(lots) - expired else "ok"},
        {"title": "SKT'si geçmiş LOT (blokajlı)", "value": expired, "url": reverse("admin:inventory_lot_changelist"),
         "level": "danger" if expired else "ok"},
        {"title": "Onay bekleyen sayım", "value": StockCount.objects.filter(status="submitted").count(),
         "url": reverse("admin:inventory_stockcount_changelist"), "level": "warning"},
    ]
