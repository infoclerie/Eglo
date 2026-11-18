"""integrations modülünün dinlediği olaylar."""
from apps.core.events import subscribe


@subscribe("accounting.send_requested")
def on_send_requested(invoice, **kw):
    from .services import active_account, enqueue
    acc = active_account("einvoice")
    if acc is None:
        return None
    return enqueue(acc, "einvoice.send", invoice.number or str(invoice.pk), {"invoice_id": invoice.pk},
                   key=f"{acc.pk}:send:{invoice.uuid}")


@subscribe("accounting.invoice_ready")
def on_invoice_ready(invoice, **kw):
    from .services import active_account
    acc = active_account("einvoice")
    if acc is None or not acc.config.get("auto_send") or invoice.direction != "out":
        return None
    from apps.accounting.services import request_send
    return request_send(invoice)
