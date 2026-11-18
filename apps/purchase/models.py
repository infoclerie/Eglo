from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.models import BaseModel
from apps.inventory.models import Warehouse
from apps.partners.models import Partner

MONEY = dict(max_digits=14, decimal_places=4)
Q3 = dict(max_digits=14, decimal_places=3)


class PurchaseRequest(BaseModel):
    """Satın alma talebi: depo/satış ihtiyacı veya sistem önerisi (§5.2 adım 1)."""

    STATUS = [("open", "Açık"), ("ordered", "Siparişe dönüştü"), ("rejected", "Reddedildi")]
    SOURCE = [("manual", "Manuel"), ("suggestion", "Sistem önerisi")]

    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    quantity = models.DecimalField("Miktar", **Q3)
    needed_by = models.DateField("İhtiyaç tarihi", null=True, blank=True)
    source = models.CharField("Kaynak", max_length=10, choices=SOURCE, default="manual")
    reason = models.CharField("Gerekçe", max_length=255, blank=True)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="open")

    class Meta:
        verbose_name, verbose_name_plural = "Satın alma talebi", "Satın alma talepleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.sku} × {self.quantity}"


class SupplierQuote(BaseModel):
    """Tedarikçi teklifi (§5.2 adım 2-3: teklif toplama ve karşılaştırma)."""

    request = models.ForeignKey(PurchaseRequest, verbose_name="Talep", null=True, blank=True,
                                on_delete=models.CASCADE, related_name="quotes")
    supplier = models.ForeignKey(Partner, verbose_name="Tedarikçi", on_delete=models.PROTECT)
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    unit_price = models.DecimalField("Birim fiyat (KDV hariç)", **MONEY)
    currency = models.CharField("Para birimi", max_length=3, default="TRY")
    lead_time_days = models.PositiveIntegerField("Termin (gün)", default=0)
    payment_term_days = models.PositiveIntegerField("Ödeme vadesi (gün)", default=0)
    min_order_qty = models.DecimalField("Minimum sipariş", **Q3, default=0)
    valid_until = models.DateField("Geçerlilik", null=True, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Tedarikçi teklifi", "Tedarikçi teklifleri"


class PurchaseOrder(BaseModel):
    STATUS = [("draft", "Taslak"), ("approval", "Onay bekliyor"), ("approved", "Onaylandı"), ("sent", "Tedarikçiye iletildi"),
              ("partial", "Kısmi teslim"), ("received", "Teslim alındı"), ("closed", "Kapandı (eksik/fazla tutanaklı)"),
              ("cancelled", "İptal")]
    OPEN = ("approved", "sent", "partial")

    number = models.CharField("Sipariş no", max_length=30, unique=True)
    supplier = models.ForeignKey(Partner, verbose_name="Tedarikçi", on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, verbose_name="Teslim deposu", on_delete=models.PROTECT)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="draft", db_index=True)
    order_date = models.DateField("Sipariş tarihi", default=timezone.localdate)
    expected_date = models.DateField("Beklenen teslim (termin)", null=True, blank=True)
    payment_term_days = models.PositiveIntegerField("Ödeme vadesi (gün)", default=0)
    currency = models.CharField("Para birimi", max_length=3, default="TRY")
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Satın alma siparişi", "Satın alma siparişleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} {self.supplier.name}"

    @property
    def total(self):
        return sum((l.quantity * l.unit_price for l in self.lines.all()), Decimal("0")).quantize(Decimal("0.01"))

    @property
    def is_late(self):
        return self.status in self.OPEN and self.expected_date and self.expected_date < timezone.localdate()


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    quantity = models.DecimalField("Sipariş miktarı", **Q3)
    unit_price = models.DecimalField("Birim fiyat (KDV hariç)", **MONEY)
    vat_rate = models.DecimalField("KDV %", max_digits=5, decimal_places=2, default=Decimal("20"))
    received_quantity = models.DecimalField("Teslim alınan", **Q3, default=0)
    request = models.ForeignKey(PurchaseRequest, verbose_name="Talep", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name, verbose_name_plural = "Satın alma satırı", "Satın alma satırları"

    def __str__(self):
        return f"{self.product.sku} × {self.quantity}"

    @property
    def open_quantity(self):
        return max(self.quantity - self.received_quantity, Decimal("0"))


class ReceiptDiscrepancy(models.Model):
    """Sipariş ile teslim alınan miktar farkı tutanağı (§3.3 ek özellik)."""

    line = models.ForeignKey(PurchaseOrderLine, verbose_name="Satır", on_delete=models.CASCADE, related_name="discrepancies")
    ordered = models.DecimalField("Sipariş", **Q3)
    received = models.DecimalField("Teslim alınan", **Q3)
    kind = models.CharField("Tür", max_length=10, choices=[("short", "Eksik teslim"), ("over", "Fazla teslim")])
    at = models.DateTimeField("Tarih", default=timezone.now)
    note = models.CharField("Not", max_length=255, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Teslim farkı tutanağı", "Teslim farkı tutanakları"
