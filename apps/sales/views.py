from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render

from apps.catalog.models import SalesChannel

from .models import SalesOrder


@login_required
@permission_required("sales.view_salesorder", raise_exception=True)
def pool(request):
    """Merkezi sipariş havuzu: tüm kanallar, durum ve o durumda bekleme süresi."""
    qs = SalesOrder.objects.select_related("channel", "customer")
    status = request.GET.get("status")
    channel_code = request.GET.get("channel")
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status__in=["delivered", "cancelled", "returned"])
    if channel_code:
        qs = qs.filter(channel__code=channel_code)

    counts = dict(SalesOrder.objects.values_list("status").annotate(n=Count("id")))
    statuses = [(code, label, counts.get(code, 0)) for code, label in SalesOrder.STATUS]

    # Kanal bazlı özet
    channels = SalesChannel.objects.filter(active=True).order_by("name")
    channel_counts = dict(
        SalesOrder.objects.exclude(status__in=["delivered", "cancelled", "returned"])
        .values_list("channel__code").annotate(n=Count("id"))
    )

    return render(request, "sales/pool.html", {
        "orders": qs[:300], "statuses": statuses, "status": status,
        "channels": channels, "channel_code": channel_code, "channel_counts": channel_counts,
    })


@login_required
@permission_required("sales.view_salesorder", raise_exception=True)
def order_detail(request, pk):
    """Sipariş detay: satırlar, durum geçmişi, kanal ve tahsilat bilgisi."""
    order = get_object_or_404(
        SalesOrder.objects.select_related("channel", "customer", "warehouse"),
        pk=pk,
    )
    lines = order.lines.select_related("product").all()
    logs = order.status_logs.select_related("user").all()
    return render(request, "sales/order_detail.html", {
        "order": order, "lines": lines, "logs": logs,
    })
