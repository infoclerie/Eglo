"""accounting modülünün dinlediği olaylar."""
from apps.core.events import subscribe
from apps.core.models import Setting

from .models import Invoice


@subscribe("shipping.shipped")
def on_shipped(order, user=None, **kw):
    if Setting.get("accounting.auto_invoice_on_ship", True):
        from .services import create_sales_invoice
        create_sales_invoice(order, user)


@subscribe("shipping.return_completed")
def on_return(return_request, user=None, **kw):
    from .services import create_return_invoice
    create_return_invoice(return_request, user)


@subscribe("partners.collect_balance")
def partner_balance(partner, **kw):
    from .services import balance
    return balance(partner)


@subscribe("approval.approved.accounting.invoice_mismatch")
def on_mismatch_approved(request, user=None, **kw):
    from .services import post_purchase_invoice
    post_purchase_invoice(Invoice.objects.get(pk=request.target_id), user)


@subscribe("approval.rejected.accounting.invoice_mismatch")
def on_mismatch_rejected(request, **kw):
    Invoice.objects.filter(pk=request.target_id).update(status="cancelled")


@subscribe("approval.approved.accounting.invoice_cancel")
def on_cancel_approved(request, user=None, **kw):
    from .services import cancel
    cancel(Invoice.objects.get(pk=request.target_id), user, request.payload.get("reason", ""))
