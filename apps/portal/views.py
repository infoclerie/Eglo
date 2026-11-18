"""Bayi portalı ekranları. Her ekran yalnızca giriş yapan bayinin kendi cari verisini gösterir."""
from datetime import date
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.accounting import services as acc
from apps.accounting.models import Invoice

from . import services
from .models import PortalAccess


def portal_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *a, **kw):
        access = PortalAccess.objects.select_related("partner").filter(user=request.user, active=True).first()
        if access is None:
            messages.error(request, "Bu hesap bayi portalına tanımlı değil.")
            return redirect("core:dashboard")
        request.partner = access.partner
        return view(request, *a, **kw)
    return wrapper


def _cart(request):
    return {int(k): int(v) for k, v in request.session.get("portal_cart", {}).items()}


def _save_cart(request, cart):
    request.session["portal_cart"] = {str(k): v for k, v in cart.items() if v > 0}


def _ctx(request, **kw):
    cart = _cart(request)
    return {"partner": request.partner, "cart_count": sum(cart.values()), **kw}


@portal_required
def home(request):
    if request.method == "POST":
        cart = _cart(request)
        try:
            pid, qty = int(request.POST["product"]), int(request.POST.get("qty") or 1)
        except (KeyError, ValueError):
            return redirect(request.path)
        cart[pid] = cart.get(pid, 0) + max(qty, 0)
        _save_cart(request, cart)
        messages.success(request, "Sepete eklendi.")
        return redirect(f"{request.path}?q={request.GET.get('q', '')}")
    q = request.GET.get("q", "").strip()
    return render(request, "portal/home.html", _ctx(request, rows=services.catalog(request.partner, q), q=q,
                                                    campaigns=services.active_campaigns(request.partner),
                                                    balance=acc.balance(request.partner)))


@portal_required
def cart(request):
    cart = _cart(request)
    if request.method == "POST":
        if request.POST.get("action") == "order":
            try:
                order, state = services.place_order(request.partner, cart, request.user, request.POST.get("note", ""))
                _save_cart(request, {})
                text = {"confirmed": f"Siparişiniz alındı: {order.number}. Hazırlanmaya başlandı.",
                        "credit_approval": f"Siparişiniz alındı: {order.number}. Kredi limitiniz aşıldığı için onay bekliyor.",
                        "stock": f"Siparişiniz alındı: {order.number}. Bazı ürünlerde stok yetersiz; satış ekibimiz sizi arayacak."}[state]
                (messages.success if state == "confirmed" else messages.warning)(request, text)
                return redirect("portal:order", pk=order.pk)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        else:
            for key, val in request.POST.items():
                if key.startswith("qty_"):
                    try:
                        cart[int(key[4:])] = max(int(val or 0), 0)
                    except ValueError:
                        pass
            _save_cart(request, cart)
            messages.success(request, "Sepet güncellendi.")
        return redirect(request.path)
    lines, total = services.cart_lines(request.partner, cart)
    vat = sum(((l["amount"] * l["p"].vat_rate / 100) for l in lines), Decimal(0)).quantize(Decimal("0.01"))
    return render(request, "portal/cart.html", _ctx(request, lines=lines, total=total, vat=vat, grand=total + vat))


@portal_required
def orders(request):
    return render(request, "portal/orders.html", _ctx(request, orders=request.partner.sales_orders.all()[:200]))


@portal_required
def order_detail(request, pk):
    order = get_object_or_404(request.partner.sales_orders, pk=pk)
    return render(request, "portal/order.html", _ctx(request, order=order, lines=order.lines.select_related("product"),
                                                     shipments=order.shipments.all(), invoices=order.invoices.exclude(status="draft")))


@portal_required
def invoices(request):
    qs = Invoice.objects.filter(partner=request.partner, direction="out").exclude(status__in=["draft", "cancelled"])
    return render(request, "portal/invoices.html", _ctx(request, invoices=qs[:200]))


@portal_required
def invoice_xml(request, pk):
    inv = get_object_or_404(Invoice, pk=pk, partner=request.partner, direction="out")
    xml = inv.xml or acc.build_xml(inv)
    resp = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + xml, content_type="application/xml; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{inv.number}.xml"'
    return resp


@portal_required
def statement(request):
    start = parse_date(request.GET.get("start") or "") or date(timezone.localdate().year, 1, 1)
    end = parse_date(request.GET.get("end") or "") or timezone.localdate()
    return render(request, "portal/statement.html", _ctx(request, st=acc.statement(request.partner, start, end), start=start, end=end))
