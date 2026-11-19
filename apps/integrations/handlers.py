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


# ---------------------------------------------------------------- pazaryeri / e-ticaret (Trendyol, Hepsiburada, ikas)
MARKET_PROVIDERS = ("trendyol", "hepsiburada", "ikas")
TRENDYOL_CARGO = {"yurtici": "YKMP", "aras": "ARASMP", "mng": "MNGMP", "surat": "SURATMP", "ptt": "PTTMP", "tex": "TEXMP"}


def _external(order):
    if order is None:
        return None
    from .models import ExternalOrder
    ext = ExternalOrder.objects.select_related("account").filter(order=order).first()
    if ext is None or not ext.account.active:
        return None
    return ext


def _q(ext, kind, label, payload, step):
    from .services import enqueue
    return enqueue(ext.account, kind, f"{ext.external_id} {label}", {"external_order_id": ext.pk, **payload},
                   key=f"{ext.account.pk}:{step}:{ext.external_id}")


@subscribe("shipping.picking_started")
def market_picking(order, **kw):
    ext = _external(order)
    if not ext or not ext.account.config.get("send_status"):
        return None
    if ext.account.provider == "trendyol":
        _q(ext, "trendyol.update_status", "Picking", {"status": "Picking"}, "ty-status-Picking")
    elif ext.account.provider == "hepsiburada":
        _q(ext, "hepsiburada.create_package", "paket", {}, "hb-package")
    return None


@subscribe("accounting.invoice_ready")
def trendyol_invoiced(invoice, **kw):
    order = invoice.sales_order
    if order is None or invoice.kind != "sale":
        return None
    ext = _external(order)
    if ext and ext.account.provider == "trendyol" and ext.account.config.get("send_status"):
        _q(ext, "trendyol.update_status", "Invoiced", {"status": "Invoiced", "params": {"invoiceNumber": invoice.number}},
           "ty-status-Invoiced")
    return None


@subscribe("shipping.shipped")
def market_shipped(order, shipment=None, **kw):
    ext = _external(order)
    if not ext or shipment is None:
        return None
    cfg, prov, tracking = ext.account.config, ext.account.provider, shipment.tracking_no or ""
    if prov == "trendyol" and cfg.get("send_tracking") and tracking:
        _q(ext, "trendyol.tracking", "takip", {"tracking_no": tracking, "provider_code": TRENDYOL_CARGO.get(shipment.carrier, "")},
           f"ty-tracking-{tracking}")
    elif prov == "hepsiburada" and cfg.get("own_cargo") and tracking:
        _q(ext, "hepsiburada.in_transit", "kargoda", {"tracking_no": tracking}, f"hb-transit-{tracking}")
    elif prov == "ikas" and cfg.get("send_status"):
        _q(ext, "ikas.fulfill", "kargolandı", {"tracking_no": tracking, "carrier": shipment.carrier}, "ikas-fulfill")
    return None


@subscribe("shipping.delivered")
def market_delivered(order, **kw):
    ext = _external(order)
    if ext and ext.account.provider == "hepsiburada" and ext.account.config.get("own_cargo"):
        _q(ext, "hepsiburada.delivered", "teslim", {}, "hb-delivered")
    return None


def _stock_changed(**kw):
    """Stok değişince pazaryeri stok gönderimini kuyruğa al (dakikada en fazla bir kez)."""
    from django.utils import timezone

    from .models import IntegrationAccount
    from .services import enqueue
    minute = int(timezone.now().timestamp() // 60)
    for acc in IntegrationAccount.objects.filter(active=True, provider__in=MARKET_PROVIDERS):
        if acc.config.get("push_stock"):
            enqueue(acc, f"{acc.provider}.push_stock", "stok-fiyat (değişiklik)", {}, key=f"{acc.pk}:stock-change:{minute}")


for _ev in ("inventory.reserved", "inventory.released", "inventory.shipped", "inventory.count_applied", "purchase.goods_received",
            "production.completed"):
    subscribe(_ev)(_stock_changed)
