from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Partner


@login_required
@permission_required("partners.view_partner", raise_exception=True)
def partner_list(request):
    qs = Partner.objects.order_by("name")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(tax_number__icontains=q)
                       | Q(phone__icontains=q) | Q(email__icontains=q))
    kind = request.GET.get("kind")
    if kind:
        qs = qs.filter(kind=kind)
    group = request.GET.get("group")
    if group:
        qs = qs.filter(group=group)
    active = request.GET.get("active", "1")
    if active == "1":
        qs = qs.filter(active=True)
    elif active == "0":
        qs = qs.filter(active=False)
    return render(request, "partners/partner_list.html", {
        "partners": qs[:500],
        "q": q,
        "kinds": Partner.KIND,
        "groups": Partner.GROUP,
        "filters": {"kind": kind or "", "group": group or "", "active": active},
    })


@login_required
@permission_required("partners.view_partner", raise_exception=True)
def partner_detail(request, pk):
    p = get_object_or_404(Partner, pk=pk)
    balance = services.open_balance(p)
    return render(request, "partners/partner_detail.html", {
        "p": p,
        "balance": balance,
    })


@login_required
@permission_required("partners.add_partner", raise_exception=True)
def partner_create(request):
    if request.method == "POST":
        try:
            p = _save_partner_form(request)
            messages.success(request, f"Cari kart oluşturuldu: {p}")
            return redirect("partners:detail", pk=p.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages) if hasattr(exc, 'messages') else str(exc))
    return render(request, "partners/partner_form.html", {
        "title": "Yeni Cari Kart",
        "kinds": Partner.KIND,
        "groups": Partner.GROUP,
    })


@login_required
@permission_required("partners.change_partner", raise_exception=True)
def partner_edit(request, pk):
    p = get_object_or_404(Partner, pk=pk)
    if request.method == "POST":
        try:
            _save_partner_form(request, p)
            messages.success(request, f"Cari kart güncellendi: {p}")
            return redirect("partners:detail", pk=p.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages) if hasattr(exc, 'messages') else str(exc))
    return render(request, "partners/partner_form.html", {
        "title": f"Düzenle: {p.code} {p.name}",
        "p": p,
        "kinds": Partner.KIND,
        "groups": Partner.GROUP,
    })


def _validate_tax_number(vkn):
    """Türkiye VKN (10 hane) veya TCKN (11 hane) doğrulama."""
    if not vkn:
        return True
    vkn = vkn.strip()
    if len(vkn) == 11 and vkn.isdigit():
        # TCKN algoritması
        digits = [int(d) for d in vkn]
        if digits[0] == 0:
            return False
        c10 = sum(digits[:10]) % 10
        if c10 != digits[10]:
            return False
        odd = sum(digits[i] for i in range(0, 9, 2))
        even = sum(digits[i] for i in range(1, 8, 2))
        c10_check = (odd * 7 - even) % 10
        return c10_check == digits[9]
    elif len(vkn) == 10 and vkn.isdigit():
        # VKN algoritması
        digits = [int(d) for d in vkn]
        total = 0
        for i in range(9):
            tmp = (digits[i] + (9 - i)) % 10
            tmp = (tmp * (2 ** (9 - i))) % 9
            if (digits[i] + (9 - i)) % 10 != 0 and tmp == 0:
                tmp = 9
            total += tmp
        return (10 - total % 10) % 10 == digits[9]
    return False


def _save_partner_form(request, partner=None):
    d = request.POST
    is_new = partner is None
    if is_new:
        partner = Partner()
    partner.name = d.get("name", "").strip()
    if not partner.name:
        raise ValidationError("Firma / kişi adı zorunludur.")
    partner.kind = d.get("kind", "customer")
    partner.group = d.get("group", "individual")
    partner.contact_person = d.get("contact_person", "")
    partner.phone = d.get("phone", "")
    partner.email = d.get("email", "")
    partner.tax_office = d.get("tax_office", "")
    tax_number = d.get("tax_number", "").strip()
    if tax_number and not _validate_tax_number(tax_number):
        raise ValidationError("Geçersiz VKN veya TC kimlik numarası. VKN 10, TCKN 11 haneli olmalıdır.")
    partner.tax_number = tax_number
    partner.e_invoice_user = d.get("e_invoice_user") == "on"
    partner.address = d.get("address", "")
    partner.shipping_address = d.get("shipping_address", "")
    partner.city = d.get("city", "")
    partner.district = d.get("district", "")
    partner.iban = d.get("iban", "")
    partner.note = d.get("note", "")
    partner.consent_sms = d.get("consent_sms") == "on"
    partner.consent_email = d.get("consent_email") == "on"
    partner.active = d.get("active", "on") == "on"
    for f in ("payment_term_days", "lead_time_days"):
        val = d.get(f, "").strip()
        if val:
            try:
                setattr(partner, f, int(val))
            except ValueError:
                pass
    for f in ("credit_limit", "discount_pct"):
        val = d.get(f, "").strip()
        if val:
            try:
                setattr(partner, f, Decimal(val))
            except InvalidOperation:
                pass
    partner.full_clean()
    partner.save()
    return partner
