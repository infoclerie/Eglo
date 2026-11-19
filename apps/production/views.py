from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.inventory.models import Warehouse
from apps.partners.models import Partner

from . import services
from .models import BillOfMaterials, ProductionOrder


def _dec(v):
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, TypeError):
        raise ValidationError("Geçerli bir sayı girin.")


class OrderForm(forms.Form):
    bom = forms.ModelChoiceField(BillOfMaterials.objects.filter(active=True), label="Reçete",
                                 help_text="Hangi ürün, hangi reçeteyle üretilecek?")
    quantity = forms.CharField(label="Üretilecek miktar", help_text="Mamul adedi (reçetedeki birimle).")
    warehouse = forms.ModelChoiceField(Warehouse.objects.all(), label="Depo", help_text="Malzemenin alınacağı ve mamulün gireceği depo.")
    kind = forms.ChoiceField(choices=ProductionOrder.KIND, label="Üretim türü", help_text="Fason: başka firmaya ürettiriyorsanız.")
    subcontractor = forms.ModelChoiceField(Partner.objects.exclude(kind="customer"), required=False, label="Fason firma",
                                           help_text="Yalnız fason üretimde seçin.")
    subcontract_unit_cost = forms.CharField(required=False, label="Fason işçilik (birim, KDV hariç)",
                                            help_text="Fasoncunun ürün başına aldığı ücret; maliyete eklenir.")
    planned_date = forms.DateField(required=False, label="Planlanan tarih", widget=forms.DateInput(attrs={"type": "date"}))
    lot_no = forms.CharField(required=False, label="Mamul LOT no", help_text="Boş bırakılırsa emir numarası LOT olur.")
    note = forms.CharField(required=False, label="Not", widget=forms.Textarea(attrs={"rows": 2}))


@login_required
@permission_required("production.view_productionorder", raise_exception=True)
def order_list(request):
    status = request.GET.get("durum", "open")
    qs = ProductionOrder.objects.select_related("product", "subcontractor")
    if status == "open":
        qs = qs.filter(status__in=ProductionOrder.OPEN)
    elif status != "all":
        qs = qs.filter(status=status)
    return render(request, "production/list.html", {"orders": qs[:300], "status": status,
                                                    "statuses": ProductionOrder.STATUS})


@login_required
@permission_required("production.add_productionorder", raise_exception=True)
def new(request):
    form = OrderForm(request.POST or None, initial={"warehouse": Warehouse.objects.first()})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            o = services.create_order(d["bom"], _dec(d["quantity"]), d["warehouse"], d["kind"], d["subcontractor"],
                                      d["planned_date"], d["lot_no"], _dec(d["subcontract_unit_cost"] or 0), d["note"], request.user)
            messages.success(request, f"{o.number} oluşturuldu. Malzeme durumunu kontrol edip 'Malzemeyi ayır' deyin.")
            return redirect("production:detail", pk=o.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    return render(request, "production/new.html", {"form": form})


@login_required
@permission_required("production.view_productionorder", raise_exception=True)
def detail(request, pk):
    o = get_object_or_404(ProductionOrder.objects.select_related("bom", "product", "warehouse", "subcontractor"), pk=pk)
    if request.method == "POST":
        if not request.user.has_perm("production.change_productionorder"):
            messages.error(request, "Bu işlem için yetkiniz yok.")
            return redirect("production:detail", pk=pk)
        action = request.POST.get("action")
        try:
            if action == "confirm":
                services.confirm(o, request.user)
                messages.success(request, "Malzemeler ayrıldı (FEFO).")
            elif action == "start":
                services.start(o, request.user)
                messages.success(request, "Malzeme sarf edildi; stoktan düştü.")
            elif action == "finish":
                services.finish(o, _dec(request.POST.get("produced_qty")), request.user)
                messages.success(request, "Mamul karantinaya alındı. Kalite kontrol bekleniyor.")
            elif action in ("qc_pass", "qc_reject"):
                services.quality_check(o, action == "qc_pass", request.POST.get("qc_note", ""), request.user)
                messages.success(request, "Kalite onaylandı, ürün satışa uygun rafa alındı." if action == "qc_pass"
                                 else "Kalite reddi kaydedildi; ürün karantinada.")
            elif action == "cancel":
                services.cancel(o, request.user)
                messages.success(request, "Emir iptal edildi, ayrılan malzeme serbest bırakıldı.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("production:detail", pk=pk)
    return render(request, "production/detail.html", {
        "o": o, "rows": services.availability(o) if o.status in ("draft", "confirmed") else [],
        "consumed": services.consumed(o)})
