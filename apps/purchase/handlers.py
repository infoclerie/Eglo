"""purchase modülünün dinlediği olaylar."""
from apps.core.events import subscribe

from .models import PurchaseOrder


@subscribe("inventory.collect_incoming")
def incoming(product, **kw):
    from .services import incoming_quantity
    return incoming_quantity(product)


@subscribe("approval.approved.purchase.order_approve")
def on_approved(request, **kw):
    PurchaseOrder.objects.filter(pk=request.target_id, status="approval").update(status="approved")


@subscribe("approval.rejected.purchase.order_approve")
def on_rejected(request, **kw):
    PurchaseOrder.objects.filter(pk=request.target_id, status="approval").update(status="draft")
