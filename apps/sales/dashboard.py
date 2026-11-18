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


def charts(request):
    """Ana panel grafikleri: son 30 gün ciro, kanal dağılımı, en çok satan ürünler."""
    from collections import OrderedDict, defaultdict
    from datetime import timedelta
    from decimal import Decimal

    from .models import SalesOrderLine
    today = timezone.localdate()
    start = today - timedelta(days=29)
    orders = SalesOrder.objects.filter(order_date__date__gte=start).exclude(status="cancelled").select_related("channel")
    days = OrderedDict(((start + timedelta(days=i)), Decimal(0)) for i in range(30))
    by_channel = defaultdict(Decimal)
    for o in orders:
        d = timezone.localtime(o.order_date).date()
        if d in days:
            days[d] += o.grand_total
        by_channel[o.channel.name] += o.grand_total
    top = defaultdict(Decimal)
    for l in SalesOrderLine.objects.filter(order__in=orders).select_related("product"):
        top[l.product.name] += l.quantity
    top = sorted(top.items(), key=lambda x: -x[1])[:8]
    return [
        {"key": "sales.chart-ciro-30", "title": "Son 30 gün ciro (KDV dahil)", "type": "line", "wide": True,
         "labels": [d.strftime("%d.%m") for d in days], "data": [float(v) for v in days.values()]},
        {"key": "sales.chart-kanal", "title": "Kanallara göre satış (30 gün)", "type": "doughnut",
         "labels": list(by_channel), "data": [float(v) for v in by_channel.values()]},
        {"key": "sales.chart-urun", "title": "En çok satan ürünler (adet, 30 gün)", "type": "bar",
         "labels": [n[:28] for n, _ in top], "data": [float(q) for _, q in top]},
    ]
