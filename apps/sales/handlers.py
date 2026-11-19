"""sales modülünün dinlediği olaylar. Sevkiyat/iade olayları sipariş durumunu ilerletir."""
from apps.core.events import subscribe

from .models import SalesOrder


def _order(request):
    return SalesOrder.objects.get(pk=request.target_id)


@subscribe("approval.approved.sales.cancel")
def on_cancel_approved(request, user=None, **kw):
    from .services import cancel
    cancel(_order(request), user, request.payload.get("reason", ""))


@subscribe("approval.approved.sales.credit_override")
def on_credit_approved(request, user=None, **kw):
    SalesOrder.objects.filter(pk=request.target_id).update(credit_approved=True)


def _status(status):
    def handler(order, user=None, **kw):
        from .services import set_status
        set_status(order, status, user)
    return handler


subscribe("shipping.picking_started")(_status("picking"))
subscribe("shipping.picked")(_status("picked"))
subscribe("shipping.packed")(_status("packed"))
subscribe("shipping.shipped")(_status("shipped"))
subscribe("shipping.delivered")(_status("delivered"))
subscribe("shipping.return_requested")(_status("return_requested"))
subscribe("shipping.return_completed")(_status("returned"))


@subscribe("core.collect_activity")
def activity_rows(start, end, q, user_id, source, extra, **kw):
    """İşlem geçmişi: sipariş durum değişiklikleri."""
    if source not in ("", "siparis") or extra.get("account"):
        return []
    from django.db.models import Q
    from django.urls import reverse

    from .models import OrderStatusLog
    qs = OrderStatusLog.objects.select_related("order", "order__channel", "user").filter(at__date__gte=start, at__date__lte=end)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if q:
        qs = qs.filter(Q(order__number__icontains=q) | Q(order__customer_name__icontains=q) | Q(order__external_ref__icontains=q))
    return [{"at": s.at, "source": "siparis", "user": s.user, "action": s.get_status_display(),
             "text": f"{s.order.number} · {s.order.channel.name} · {s.order.customer_name}", "detail": s.note,
             "url": reverse("admin:sales_salesorder_change", args=[s.order_id]), "level": "danger" if s.status == "cancelled" else ""}
            for s in qs.order_by("-at")[:300]]
