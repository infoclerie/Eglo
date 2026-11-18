"""Sistem olaylarını bildirim merkezine bağlar."""
from django.db.models.signals import post_save
from django.urls import reverse

from apps.core.events import subscribe

from .services import notify


def _money(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _order_fields(order):
    return {"siparis_no": order.number, "musteri": order.display_customer or "", "tutar": _money(order.grand_total), "kanal": str(order.channel)}


def _customer(order):
    return {"email": order.email or (order.customer.email if order.customer else ""),
            "phone": order.phone or (order.customer.phone if order.customer else ""), "ref": order.number}


@subscribe("sales.order_confirmed")
def order_new(order, **kw):
    notify("order_new", _order_fields(order), reverse("sales:pool"))
    notify("order_received", _order_fields(order), customer=_customer(order))
    from apps.inventory.services import stock_summary
    for line in order.lines.select_related("product"):
        p = line.product
        if p.min_stock and not p.is_kit:
            avail = stock_summary(p)["available"]
            if avail < p.min_stock:
                notify("low_stock", {"urun": f"{p.sku} {p.name}", "stok": avail, "minimum": p.min_stock},
                       reverse("inventory:summary") + "?low=1", once_key=p.pk)


@subscribe("sales.order_cancelled")
def order_cancelled(order, **kw):
    notify("order_cancelled", _order_fields(order), reverse("sales:pool"))


@subscribe("approval.requested")
def approval(request, **kw):
    notify("approval_requested", {"baslik": request.title, "talep_eden": str(request.requested_by or "-")},
           reverse("admin:core_approvalrequest_changelist") + "?status__exact=pending")


@subscribe("shipping.shipped")
def shipped(order, shipment=None, **kw):
    notify("order_shipped", {**_order_fields(order), "kargo": shipment.get_carrier_display() if shipment else "",
                             "takip_no": (shipment.tracking_no if shipment else "") or "-"}, customer=_customer(order))


@subscribe("shipping.delivered")
def delivered(order, **kw):
    notify("order_delivered", _order_fields(order), customer=_customer(order))


@subscribe("accounting.invoice_ready")
def invoice(invoice, **kw):
    if invoice.kind != "sale":
        return
    p = invoice.partner
    notify("invoice_issued", {"musteri": invoice.buyer_title, "fatura_no": invoice.number, "tutar": _money(invoice.total),
                              "vade": invoice.due_date.strftime("%d.%m.%Y") if invoice.due_date else "-"},
           customer={"email": invoice.buyer_email or (p.email if p else ""), "phone": p.phone if p else "", "ref": invoice.number})


@subscribe("accounting.payment_registered")
def payment(payment, **kw):
    if payment.direction != "in":
        return
    from apps.partners.services import open_balance
    p = payment.partner
    notify("payment_received", {"musteri": p.name, "tutar": _money(payment.amount), "tarih": payment.date.strftime("%d.%m.%Y"),
                                "bakiye": _money(open_balance(p))}, customer={"email": p.email, "phone": p.phone, "ref": f"PAY{payment.pk}"})


@subscribe("integrations.job_failed")
def job_failed(job, error="", **kw):
    if job.kind.startswith("notify."):
        return
    notify("integration_failed", {"baglanti": str(job.account), "is": job.kind, "hata": error[:300]}, reverse("integrations:jobs") + "?status=failed")


def partner_created(sender, instance, created, raw=False, **kw):
    if created and not raw and instance.is_customer:
        notify("partner_created", {"musteri": instance.name, "cari_kodu": instance.code},
               customer={"email": instance.email, "phone": instance.phone, "ref": instance.code})


def connect():
    from django.apps import apps
    if apps.is_installed("apps.partners"):
        post_save.connect(partner_created, sender="partners.Partner", dispatch_uid="notify_partner_created")
