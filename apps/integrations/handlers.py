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


# ---------------------------------------------------------------- pazaryeri (Trendyol)
def _external(order):
    ext = getattr(order, "external", None) if order is not None else None
    if ext is None or not ext.account.active or not ext.account.config.get("send_status"):
        return None
    return ext


@subscribe("shipping.picking_started")
def trendyol_picking(order, **kw):
    from apps.sales.models import SalesOrder
    try:
        ext = _external(order)
    except SalesOrder.external.RelatedObjectDoesNotExist:
        return None
    if ext and ext.account.provider == "trendyol":
        from .services import enqueue
        enqueue(ext.account, "trendyol.update_status", f"{ext.external_id} Picking",
                {"external_order_id": ext.pk, "status": "Picking"}, key=f"{ext.account.pk}:ty-status:{ext.external_id}:Picking")


@subscribe("accounting.invoice_ready")
def trendyol_invoiced(invoice, **kw):
    order = invoice.sales_order
    if order is None or invoice.kind != "sale":
        return None
    from apps.sales.models import SalesOrder
    try:
        ext = _external(order)
    except SalesOrder.external.RelatedObjectDoesNotExist:
        return None
    if ext and ext.account.provider == "trendyol":
        from .services import enqueue
        enqueue(ext.account, "trendyol.update_status", f"{ext.external_id} Invoiced",
                {"external_order_id": ext.pk, "status": "Invoiced", "params": {"invoiceNumber": invoice.number}},
                key=f"{ext.account.pk}:ty-status:{ext.external_id}:Invoiced")
    return None


def _stock_changed(**kw):
    """Stok değişince pazaryeri stok gönderimini kuyruğa al (dakikada en fazla bir kez)."""
    from django.utils import timezone

    from .models import IntegrationAccount
    from .services import enqueue
    minute = int(timezone.now().timestamp() // 60)
    for acc in IntegrationAccount.objects.filter(active=True, provider="trendyol"):
        if acc.config.get("push_stock"):
            enqueue(acc, "trendyol.push_stock", "stok-fiyat (değişiklik)", {}, key=f"{acc.pk}:ty-stock-change:{minute}")


for _ev in ("inventory.reserved", "inventory.released", "inventory.shipped", "inventory.count_applied", "purchase.goods_received"):
    subscribe(_ev)(_stock_changed)
