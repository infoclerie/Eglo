from django.urls import reverse
from django.utils import timezone

from .models import SalesOrder


def widgets(request):
    today = timezone.localdate()
    todays = SalesOrder.objects.filter(order_date__date=today).exclude(status="cancelled")
    total = sum((o.grand_total for o in todays), 0)
    waiting = SalesOrder.objects.filter(status__in=["reserved", "picking", "picked", "packed", "invoiced"]).count()
    pool = reverse("sales:pool")
    return [
        {"title": "Bugünkü sipariş", "value": todays.count(), "url": pool, "level": "ok"},
        {"title": "Bugünkü ciro (KDV dahil)", "value": f"{total:,.2f} TL", "url": pool, "level": "ok"},
        {"title": "Sevkiyat bekleyen sipariş", "value": waiting, "url": pool, "level": "warning" if waiting else "ok"},
    ]
