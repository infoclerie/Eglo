from django import forms

from apps.catalog.models import Product

from .models import Location, Lot, Pallet


def _product_field():
    return forms.ModelChoiceField(Product.objects.filter(active=True).exclude(kind="kit"), label="Ürün")


def _location_field(label):
    return forms.ModelChoiceField(Location.objects.filter(active=True).exclude(kind__in=Location.VIRTUAL_KINDS), label=label)


class ReceiveForm(forms.Form):
    product = _product_field()
    quantity = forms.DecimalField(label="Miktar", min_value=0.001)
    location = _location_field("Yerleşim lokasyonu")
    lot_no = forms.CharField(label="LOT / parti no", required=False)
    production_date = forms.DateField(label="Üretim tarihi", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    expiry_date = forms.DateField(label="SKT", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    pallet = forms.ModelChoiceField(Pallet.objects.filter(active=True), label="Palet", required=False)
    reference = forms.CharField(label="İrsaliye / sipariş no", required=False)
    move_type = forms.ChoiceField(label="Giriş türü", choices=[("purchase_in", "Satın alma girişi"), ("production_in", "Üretimden giriş")])


class TransferForm(forms.Form):
    product = _product_field()
    quantity = forms.DecimalField(label="Miktar", min_value=0.001)
    source = _location_field("Kaynak lokasyon")
    destination = _location_field("Hedef lokasyon")
    lot = forms.ModelChoiceField(Lot.objects.all(), label="LOT", required=False)
    pallet = forms.ModelChoiceField(Pallet.objects.filter(active=True), label="Palet", required=False)
    note = forms.CharField(label="Not", required=False)
