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
