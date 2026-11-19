from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.catalog.models import Product

from . import services
from .forms import ReceiveForm, TransferForm
from .models import Location, Pallet, Quant


@login_required
@permission_required("inventory.view_quant", raise_exception=True)
def summary(request):
    if request.method == "POST" and request.POST.get("setup_warehouse") and request.user.has_perm("inventory.add_location"):
        wh, new = services.ensure_default_warehouse()
        messages.success(request, f"'{wh}' deposu ve raf lokasyonları oluşturuldu (A-01-01-01 …). Depo ve raf adlarını Yönetim › Lokasyonlar'dan değiştirebilirsiniz."
                         if new else "Zaten tanımlı bir depo var.")
        return redirect(request.path)
    products = Product.objects.filter(active=True).select_related("brand").order_by("sku")
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(Q(sku__icontains=q) | Q(name__icontains=q) | Q(barcode=q))
    rows = []
    for p in products[:500]:
        s = services.stock_summary(p)
        low = (not p.is_kit) and p.min_stock > 0 and s["available"] < p.min_stock
        if request.GET.get("low") and not low:
            continue
        rows.append({"p": p, "s": s, "low": low})
    from .models import Warehouse
    return render(request, "inventory/summary.html", {"rows": rows, "q": q, "no_warehouse": not Warehouse.objects.exists(),
                                                      "no_products": not Product.objects.exists()})


@login_required
@permission_required("inventory.view_quant", raise_exception=True)
def scan(request):
    """El terminali / barkod okuyucu: ürün, lokasyon veya palet barkodu okutulur."""
    code = request.GET.get("code", "").strip()
    ctx = {"code": code}
    if code:
        product = Product.objects.filter(Q(barcode=code) | Q(case_barcode=code) | Q(sku=code)).first()
        location = Location.objects.filter(Q(barcode=code) | Q(code=code)).first()
        pallet = Pallet.objects.filter(code=code).first()
        quants = Quant.objects.filter(quantity__gt=0).select_related("product", "location", "lot", "pallet")
        if product:
            quants = quants.filter(product=product)
            ctx.update(product=product, summary=services.stock_summary(product), images=list(product.images.all()[:6]))
        elif location:
            quants = quants.filter(location=location)
            ctx["location"] = location
        elif pallet:
            quants = quants.filter(pallet=pallet)
            ctx["pallet"] = pallet
        else:
            quants = quants.none()
            ctx["not_found"] = True
        ctx["quants"] = [{"q": x, "code": services.expiry_status(x.lot) or "",
                          "status": services.EXPIRY_LABELS.get(services.expiry_status(x.lot), "LOT yok")}
                         for x in quants.order_by("lot__expiry_date")]
    return render(request, "inventory/scan.html", ctx)


def _run_form(request, form_cls, action, title, photos=False):
    form = form_cls(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            move = action(form.cleaned_data, request.user)
            msg = f"Kaydedildi: {move}"
            if photos and request.FILES.getlist("photos"):
                from apps.catalog.views import save_photos
                n = save_photos(request, form.cleaned_data["product"], f"Mal kabul {form.cleaned_data.get('reference') or ''}".strip())
                msg += f" · {n} fotoğraf eklendi"
            messages.success(request, msg)
            return redirect(request.path)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "inventory/form.html", {"form": form, "title": title, "photos": photos})


@login_required
@permission_required("inventory.add_stockmove", raise_exception=True)
def receive(request):
    def action(d, user):
        return services.receive(d["product"], d["quantity"], d["location"], lot_no=d["lot_no"] or None,
                                expiry_date=d["expiry_date"], production_date=d["production_date"],
                                reference=d["reference"], user=user, move_type=d["move_type"], pallet=d["pallet"])
    return _run_form(request, ReceiveForm, action, "Mal Kabul", photos=True)


@login_required
@permission_required("inventory.add_stockmove", raise_exception=True)
def transfer(request):
    def action(d, user):
        return services.transfer(d["product"], d["quantity"], d["source"], d["destination"], lot=d["lot"],
                                 pallet=d["pallet"], user=user, note=d["note"])
    return _run_form(request, TransferForm, action, "Stok Transferi")
