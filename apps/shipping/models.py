from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import BaseModel
from apps.inventory.models import Location, Lot
from apps.sales.models import SalesOrder

Q3 = dict(max_digits=14, decimal_places=3)

CARRIERS = [("yurtici", "Yurtiçi Kargo"), ("aras", "Aras Kargo"), ("mng", "MNG Kargo"), ("surat", "Sürat Kargo"),
            ("ptt", "PTT Kargo"), ("hepsijet", "Hepsijet"), ("tex", "Trendyol Express"), ("own", "Kendi aracımız"),
            ("other", "Diğer lojistik")]


class Shipment(BaseModel):
    STATUS = [("waiting", "Toplama bekliyor"), ("picking", "Toplanıyor"), ("picked", "Toplandı"),
              ("packed", "Paketlendi"), ("shipped", "Sevk edildi"), ("delivered", "Teslim edildi"),
              ("cancelled", "İptal")]
    METHOD = [("single", "Tekli toplama"), ("batch", "Çoklu toplama"), ("wave", "Dalga toplama"),
              ("zone", "Bölge bazlı"), ("pallet", "Palet toplama")]

    number = models.CharField("Sevk no", max_length=30, unique=True)
    order = models.ForeignKey(SalesOrder, verbose_name="Sipariş", on_delete=models.PROTECT, related_name="shipments")
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="waiting", db_index=True)
    method = models.CharField("Toplama yöntemi", max_length=10, choices=METHOD, default="single")
    priority = models.PositiveSmallIntegerField("Öncelik", default=5, help_text="1 en acil")
    picker = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Toplayan", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")
    carrier = models.CharField("Kargo / taşıyıcı", max_length=10, choices=CARRIERS, blank=True)
    tracking_no = models.CharField("Takip no", max_length=60, blank=True, db_index=True)
    package_count = models.PositiveIntegerField("Koli adedi", default=0)
    weight_kg = models.DecimalField("Tartılan ağırlık (kg)", **Q3, null=True, blank=True)
    expected_weight_kg = models.DecimalField("Beklenen ağırlık (kg)", **Q3, default=0)
    vehicle_plate = models.CharField("Plaka", max_length=15, blank=True)
    driver_name = models.CharField("Şoför", max_length=100, blank=True)
    delivery_appointment = models.DateTimeField("Teslimat randevusu", null=True, blank=True)
    received_by = models.CharField("Teslim alan", max_length=100, blank=True)
    delivery_note = models.TextField("Teslimat tutanağı / eksik-hasar notu", blank=True)
    shipped_at = models.DateTimeField("Sevk zamanı", null=True, blank=True)
    delivered_at = models.DateTimeField("Teslim zamanı", null=True, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Sevkiyat", "Sevkiyatlar"
        ordering = ["priority", "created_at"]

    def __str__(self):
        return f"{self.number} ({self.order})"


class ShipmentLine(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    location = models.ForeignKey(Location, verbose_name="Toplama lokasyonu", on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, verbose_name="LOT", null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.DecimalField("Toplanacak", **Q3)
    picked_quantity = models.DecimalField("Toplanan", **Q3, default=0)

    class Meta:
        verbose_name, verbose_name_plural = "Toplama satırı", "Toplama satırları"
        ordering = ["location__code"]

    @property
    def remaining(self):
        return self.quantity - self.picked_quantity


class ReturnRequest(BaseModel):
    REASON = [("damaged", "Hasarlı geldi"), ("wrong", "Yanlış ürün"), ("changed_mind", "Vazgeçti"),
              ("expiry", "SKT sorunu"), ("quality", "Kalite şikâyeti"), ("other", "Diğer")]
    STATUS = [("requested", "Talep açıldı"), ("received", "Depoya ulaştı"), ("inspected", "Kontrol edildi, onay bekliyor"),
              ("completed", "Tamamlandı"), ("rejected", "Reddedildi")]

    number = models.CharField("İade no", max_length=30, unique=True)
    order = models.ForeignKey(SalesOrder, verbose_name="Sipariş", on_delete=models.PROTECT, related_name="returns")
    reason = models.CharField("İade nedeni", max_length=15, choices=REASON)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="requested")
    return_code = models.CharField("İade kargo kodu", max_length=40, blank=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "İade", "İadeler"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class ReturnLine(models.Model):
    CONDITION = [("sellable", "Satılabilir"), ("opened", "Açılmış / kullanılmış"), ("damaged", "Hasarlı"),
                 ("quarantine", "Karantina (kontrol gerekli)")]

    request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    quantity = models.DecimalField("Miktar", **Q3)
    lot = models.ForeignKey(Lot, verbose_name="LOT", null=True, blank=True, on_delete=models.PROTECT)
    condition = models.CharField("Ürün durumu", max_length=10, choices=CONDITION, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "İade satırı", "İade satırları"
