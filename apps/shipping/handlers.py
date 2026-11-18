"""shipping modülünün dinlediği olaylar."""
from apps.core.events import subscribe

from .models import ReturnRequest, Shipment


@subscribe("sales.order_confirmed")
def on_order_confirmed(order, **kw):
    from .services import create_shipment
    create_shipment(order)


@subscribe("sales.order_cancelled")
def on_order_cancelled(order, **kw):
    Shipment.objects.filter(order=order).exclude(status__in=["shipped", "delivered"]).update(status="cancelled")


@subscribe("approval.approved.shipping.return_accept")
def on_return_approved(request, user=None, **kw):
    from .services import complete_return
    complete_return(ReturnRequest.objects.get(pk=request.target_id), user)


@subscribe("approval.rejected.shipping.return_accept")
def on_return_rejected(request, **kw):
    ReturnRequest.objects.filter(pk=request.target_id).update(status="rejected")
