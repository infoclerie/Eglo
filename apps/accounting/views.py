from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.catalog.models import SalesChannel
from apps.partners.models import Partner

from . import services
from .models import Account, Invoice, LedgerEntry

TABS = [("out", "Giden faturalar"), ("in", "Gelen faturalar"), ("problem", "Hata / onay bekleyen"), ("draft", "Taslaklar")]


@login_required
@permission_required("accounting.view_invoice", raise_exception=True)
def invoices(request):
    tab = request.GET.get("tab", "out")
    qs = Invoice.objects.select_related("partner", "sales_order")
    qs = {"out": qs.filter(direction="out").exclude(status="draft"), "in": qs.filter(direction="in"),
          "problem": qs.filter(status__in=["error", "on_hold", "rejected"]), "draft": qs.filter(status="draft")}.get(tab, qs)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(buyer_title__icontains=q) | Q(buyer_vkn=q) | Q(sales_order__number=q))
    counts = {"problem": Invoice.objects.filter(status__in=["error", "on_hold", "rejected"]).count(),
              "draft": Invoice.objects.filter(status="draft").count()}
    return render(request, "accounting/invoices.html", {"invoices": qs[:300], "tab": tab, "tabs": TABS, "q": q, "counts": counts})


@login_required
@permission_required("accounting.view_invoice", raise_exception=True)
def invoice_detail(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related("partner", "sales_order", "purchase_order"), pk=pk)
    if request.method == "POST":
        if not request.user.has_perm("accounting.change_invoice"):
            messages.error(request, "Bu işlem için yetkiniz yok.")
            return redirect(request.path)
        action = request.POST.get("action")
        try:
            if action == "issue":
                services.issue(inv, request.user)
                messages.success(request, f"Fatura kesildi: {inv.number}")
            elif action == "send":
                services.request_send(inv, request.user)
                messages.success(request, "Fatura gönderim kuyruğuna alındı.")
            elif action == "cancel":
                services.request_cancel(inv, request.user, request.POST.get("reason", ""))
                messages.success(request, "İptal talebi yönetici onayına gönderildi.")
            elif action == "payment":
                services.register_payment(inv.partner, Account.objects.get(pk=request.POST["account"]),
                                          request.POST["amount"], "in" if inv.direction == "out" else "out",
                                          parse_date(request.POST.get("date") or "") or None,
                                          request.POST.get("method", "transfer"), invoice=inv,
                                          reference=request.POST.get("reference", ""), user=request.user)
                messages.success(request, "Tahsilat / ödeme kaydedildi.")
        except (ValidationError, Account.DoesNotExist, KeyError) as exc:
            messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(request.path)
    return render(request, "accounting/invoice.html", {
        "inv": inv, "lines": inv.lines.select_related("product"), "accounts": Account.objects.filter(active=True),
        "payments": inv.payments.select_related("account"), "today": timezone.localdate()})


@login_required
@permission_required("accounting.view_invoice", raise_exception=True)
def invoice_xml(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    try:
        xml = inv.xml or services.build_xml(inv)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("accounting:invoice", pk=pk)
    resp = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + xml, content_type="application/xml; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{inv.number or inv.pk}.xml"'
    return resp


@login_required
@permission_required("accounting.view_ledgerentry", raise_exception=True)
def balances(request):
    rows = (LedgerEntry.objects.values("partner", "partner__code", "partner__name", "partner__kind", "partner__credit_limit")
            .annotate(d=Sum("debit"), c=Sum("credit")).order_by("partner__name"))
    data = [{**r, "balance": (r["d"] or 0) - (r["c"] or 0)} for r in rows]
    data = [r for r in data if r["balance"] != 0] if request.GET.get("open") else data
    overdue = services.overdue_receivables()
    return render(request, "accounting/balances.html", {"rows": data, "overdue": overdue[:50]})


@login_required
@permission_required("accounting.view_ledgerentry", raise_exception=True)
def statement_view(request, partner_id):
    partner = get_object_or_404(Partner, pk=partner_id)
    start = parse_date(request.GET.get("start") or "") or date(timezone.localdate().year, 1, 1)
    end = parse_date(request.GET.get("end") or "") or timezone.localdate()
    return render(request, "accounting/statement.html", {"partner": partner, "st": services.statement(partner, start, end),
                                                         "start": start, "end": end})


@login_required
@permission_required("accounting.view_invoice", raise_exception=True)
def cashflow(request):
    return render(request, "accounting/cashflow.html", {"rows": services.cash_flow()})


@login_required
@permission_required("accounting.view_invoice", raise_exception=True)
def profitability(request):
    end = parse_date(request.GET.get("end") or "") or timezone.localdate()
    start = parse_date(request.GET.get("start") or "") or end - timedelta(days=30)
    channel = SalesChannel.objects.filter(code=request.GET.get("channel")).first()
    rows = services.product_profitability(start, end, channel)
    tot = {k: sum((r.get(k, 0) for r in rows), 0) for k in ("revenue", "product_cost", "commission", "shipping", "contribution")}
    return render(request, "accounting/profitability.html", {"rows": rows, "tot": tot, "start": start, "end": end,
                                                             "channels": SalesChannel.objects.all(), "channel": channel})
