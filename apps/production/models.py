"""Üretim ve fason (müşteri dokümanı §10): reçete (BOM), üretim emri, hammadde sarfı, kalite kontrol → karantina."""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import BaseModel

Q3 = {"max_digits": 14, "decimal_places": 3}


class BillOfMaterials(BaseModel):
    product = models.ForeignKey(Product, verbose_name="Mamul", on_delete=models.PROTECT, related_name="boms",
                                help_text="Bu reçeteyle üretilen ürün.")
    code = models.CharField("Reçete kodu", max_length=40, unique=True, help_text="Örn: RCT-SERUM-01")
    batch_size = models.DecimalField("Parti büyüklüğü", **Q3, default=1,
                                     help_text="Aşağıdaki malzeme miktarları bu kadar mamul için yazılır (ör. 1000 adet).")
    active = models.BooleanField("Aktif", default=True)
    note = models.TextField("Üretim notu / talimat", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Reçete", "Reçeteler"
        ordering = ["product__name"]

    def __str__(self):
        return f"{self.code} · {self.product.name}"


class BomLine(models.Model):
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name="lines")
    component = models.ForeignKey(Product, verbose_name="Hammadde / ambalaj", on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField("Miktar (parti başına)", **Q3)
    scrap_pct = models.DecimalField("Fire payı %", max_digits=5, decimal_places=2, default=0,
                                    help_text="Üretimde beklenen kayıp; ihtiyaç bu oranda artırılır.")

    class Meta:
        verbose_name, verbose_name_plural = "Reçete satırı", "Reçete satırları"

    def __str__(self):
        return f"{self.component} × {self.quantity}"


class ProductionOrder(BaseModel):
    STATUS = [("draft", "Taslak"), ("confirmed", "Malzeme ayrıldı"), ("in_progress", "Üretimde"),
              ("at_subcontractor", "Fasoncuda"), ("qc", "Kalite kontrolde (karantina)"), ("done", "Tamamlandı"),
              ("rejected", "Kalite reddi"), ("cancelled", "İptal")]
    KIND = [("internal", "İç üretim"), ("subcontract", "Fason üretim")]
    OPEN = ("draft", "confirmed", "in_progress", "at_subcontractor", "qc")

    number = models.CharField("Emir no", max_length=30, unique=True)
    kind = models.CharField("Üretim türü", max_length=12, choices=KIND, default="internal")
    bom = models.ForeignKey(BillOfMaterials, verbose_name="Reçete", on_delete=models.PROTECT, related_name="orders")
    product = models.ForeignKey(Product, verbose_name="Mamul", on_delete=models.PROTECT, related_name="production_orders")
    warehouse = models.ForeignKey("inventory.Warehouse", verbose_name="Depo", on_delete=models.PROTECT)
    subcontractor = models.ForeignKey("partners.Partner", verbose_name="Fason firma", null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="+")
    subcontract_unit_cost = models.DecimalField("Fason işçilik (birim)", max_digits=14, decimal_places=4, default=0)
    planned_qty = models.DecimalField("Planlanan miktar", **Q3)
    produced_qty = models.DecimalField("Üretilen miktar", **Q3, default=0)
    planned_date = models.DateField("Planlanan tarih", null=True, blank=True)
    lot_no = models.CharField("Mamul LOT no", max_length=50, blank=True, help_text="Boş bırakılırsa emir numarası kullanılır.")
    production_date = models.DateField("Üretim tarihi", null=True, blank=True)
    expiry_date = models.DateField("SKT", null=True, blank=True, help_text="Boşsa ürünün raf ömründen hesaplanır.")
    status = models.CharField("Durum", max_length=16, choices=STATUS, default="draft", db_index=True)
    material_cost = models.DecimalField("Sarf edilen malzeme maliyeti", max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Birim maliyet", max_digits=14, decimal_places=4, default=0)
    qc_note = models.TextField("Kalite kontrol notu", blank=True)
    qc_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Kontrol eden", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Üretim emri", "Üretim emirleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} · {self.product.name}"

    @property
    def waste_pct(self):
        """Planlanan ile üretilen arasındaki kayıp oranı."""
        if not self.planned_qty or not self.produced_qty:
            return Decimal("0")
        return ((self.planned_qty - self.produced_qty) / self.planned_qty * 100).quantize(Decimal("0.01"))
