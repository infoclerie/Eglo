from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.shortcuts import render

from .models import SalesOrder


@login_required
@permission_required("sales.view_salesorder", raise_exception=True)
def pool(request):
    """Merkezi sipariş havuzu: tüm kanallar, durum ve o durumda bekleme süresi."""
    qs = SalesOrder.objects.select_related("channel", "customer")
    status = request.GET.get("status")
    channel = request.GET.get("channel")
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status__in=["delivered", "cancelled", "returned"])
    if channel:
        qs = qs.filter(channel__code=channel)
    counts = dict(SalesOrder.objects.values_list("status").annotate(n=Count("id")))
    statuses = [(code, label, counts.get(code, 0)) for code, label in SalesOrder.STATUS]
    return render(request, "sales/pool.html", {"orders": qs[:300], "statuses": statuses, "status": status})
