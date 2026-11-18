from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.models import BaseModel

Q3 = dict(max_digits=14, decimal_places=3)


class Warehouse(BaseModel):
    code = models.CharField("Depo kodu", max_length=10, unique=True)
    name = models.CharField("Depo adı", max_length=100)
    external = models.BooleanField("Dış lojistik deposu", default=False)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Depo", "Depolar"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Location(BaseModel):
    """
    Fiziksel veya sanal lokasyon. Kod biçimi: DEPO-KORİDOR-RAF-KAT (ör. A-02-03-01).
    Sanal lokasyonlar (tedarikçi, müşteri, üretim, sayım farkı, fire) stok tutmaz; hareketin karşı tarafıdır.
    """

    KIND = [
        ("storage", "Raf / stok alanı"), ("receiving", "Mal kabul alanı"), ("shipping", "Sevkiyat alanı"),
        ("return_check", "İade kontrol alanı"), ("quarantine", "Karantina"), ("damaged", "Hasarlı ürün"),
        ("sample", "Numune / tester"), ("transit", "Yolda / transfer"),
        # sanal
        ("supplier", "Sanal: Tedarikçi"), ("customer", "Sanal: Müşteri"), ("production", "Sanal: Üretim"),
        ("adjustment", "Sanal: Sayım farkı"), ("scrap", "Sanal: Fire / imha"),
    ]
    VIRTUAL_KINDS = {"supplier", "customer", "production", "adjustment", "scrap"}

    warehouse = models.ForeignKey(Warehouse, verbose_name="Depo", null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="locations")
    code = models.CharField("Lokasyon kodu", max_length=30, unique=True)
    name = models.CharField("Ad", max_length=100, blank=True)
    kind = models.CharField("Tür", max_length=15, choices=KIND, default="storage")
    aisle = models.CharField("Koridor", max_length=10, blank=True)
    rack = models.CharField("Raf", max_length=10, blank=True)
    level = models.CharField("Kat / göz", max_length=10, blank=True)
    barcode = models.CharField("Barkod", max_length=40, unique=True, null=True, blank=True)
    is_sellable = models.BooleanField("Satışa uygun stok", default=True,
                                      help_text="Sadece raf/stok alanlarında işaretli olmalı.")
    can_receive = models.BooleanField("Ürün kabul edebilir", default=True)
    can_pick = models.BooleanField("Toplama yapılabilir", default=True)
    max_weight_kg = models.DecimalField("Maks. taşıma (kg)", **Q3, default=0)
    max_volume_m3 = models.DecimalField("Maks. hacim (m³)", **Q3, default=0)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Lokasyon", "Lokasyonlar"
        ordering = ["code"]

    def __str__(self):
        return self.code

    @property
    def is_virtual(self):
        return self.kind in self.VIRTUAL_KINDS

    def save(self, *args, **kwargs):
        if self.kind != "storage" and self._state.adding and self.is_sellable:
            self.is_sellable = False
        if not self.barcode and not self.is_virtual:
            self.barcode = self.code
        super().save(*args, **kwargs)


class Lot(BaseModel):
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT, related_name="lots")
    lot_no = models.CharField("LOT / parti no", max_length=50)
    production_date = models.DateField("Üretim tarihi", null=True, blank=True)
    expiry_date = models.DateField("Son kullanma tarihi", null=True, blank=True, db_index=True)
    producer = models.CharField("Üretici / tedarikçi", max_length=150, blank=True)
    origin = models.CharField("Üretim yeri", max_length=150, blank=True)
    received_at = models.DateTimeField("Depoya giriş", default=timezone.now)

    class Meta:
        verbose_name, verbose_name_plural = "LOT / parti", "LOT / partiler"
        unique_together = [("product", "lot_no")]
        ordering = ["expiry_date", "received_at"]

    def __str__(self):
        return f"{self.lot_no} (SKT {self.expiry_date or '-'})"

    def days_to_expiry(self, today=None):
        if not self.expiry_date:
            return None
        return (self.expiry_date - (today or timezone.localdate())).days


class Pallet(BaseModel):
    code = models.CharField("Palet barkodu", max_length=40, unique=True)
    location = models.ForeignKey(Location, verbose_name="Lokasyon", null=True, blank=True,
                                 on_delete=models.PROTECT, related_name="pallets")
    max_cases = models.PositiveIntegerField("Kapasite (koli)", default=0)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Palet", "Paletler"

    def __str__(self):
        return self.code


class Quant(models.Model):
    """Anlık stok: ürün + lokasyon + LOT + palet başına miktar. Sadece services.py değiştirir."""

    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT, related_name="quants")
    location = models.ForeignKey(Location, verbose_name="Lokasyon", on_delete=models.PROTECT, related_name="quants")
    lot = models.ForeignKey(Lot, verbose_name="LOT", null=True, blank=True, on_delete=models.PROTECT, related_name="quants")
    pallet = models.ForeignKey(Pallet, verbose_name="Palet", null=True, blank=True, on_delete=models.PROTECT, related_name="quants")
    quantity = models.DecimalField("Miktar", **Q3, default=0)
    reserved_quantity = models.DecimalField("Rezerve", **Q3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name, verbose_name_plural = "Stok (lokasyon bazlı)", "Stoklar (lokasyon bazlı)"
        indexes = [models.Index(fields=["product", "location"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="quant_qty_non_negative"),
            models.CheckConstraint(condition=models.Q(reserved_quantity__gte=0), name="quant_reserved_non_negative"),
            models.CheckConstraint(condition=models.Q(reserved_quantity__lte=models.F("quantity")), name="quant_reserved_lte_qty"),
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.location} {self.lot or ''}: {self.quantity}"

    @property
    def free_quantity(self):
        return self.quantity - self.reserved_quantity


class StockMove(models.Model):
    """Değiştirilemez stok hareket kaydı (her giriş/çıkış/transfer)."""

    TYPE = [
        ("purchase_in", "Satın alma girişi"), ("production_in", "Üretimden giriş"),
        ("sale_out", "Satış sevkiyatı"), ("customer_return", "Müşteri iadesi"),
        ("supplier_return", "Tedarikçi iadesi"), ("transfer", "Transfer"), ("scrap", "Fire / hasar"),
        ("sample_out", "Numune çıkışı"), ("promo_out", "Promosyon çıkışı"), ("count_adjust", "Sayım farkı"),
        ("production_consume", "Üretime sarf"),
    ]

    date = models.DateTimeField("Tarih", default=timezone.now, db_index=True)
    move_type = models.CharField("Hareket türü", max_length=20, choices=TYPE, db_index=True)
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT, related_name="moves")
    quantity = models.DecimalField("Miktar", **Q3)
    source = models.ForeignKey(Location, verbose_name="Kaynak", on_delete=models.PROTECT, related_name="moves_out")
    destination = models.ForeignKey(Location, verbose_name="Hedef", on_delete=models.PROTECT, related_name="moves_in")
    lot = models.ForeignKey(Lot, verbose_name="LOT", null=True, blank=True, on_delete=models.PROTECT)
    pallet = models.ForeignKey(Pallet, verbose_name="Palet", null=True, blank=True, on_delete=models.PROTECT)
    unit_cost = models.DecimalField("Birim maliyet", max_digits=14, decimal_places=4, default=0)
    reference = models.CharField("Referans", max_length=100, blank=True, db_index=True,
                                 help_text="Sipariş no, irsaliye no, sayım no ...")
    note = models.CharField("Not", max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="İşlem yapan", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name, verbose_name_plural = "Stok hareketi", "Stok hareketleri"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_move_type_display()} {self.product.sku} {self.quantity} {self.source}→{self.destination}"


class Reservation(models.Model):
    """Bir referansa (sipariş vb.) ayrılmış stok. FEFO ile quant seçilir."""

    reference = models.CharField("Referans", max_length=100, db_index=True)
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    quant = models.ForeignKey(Quant, verbose_name="Stok", on_delete=models.PROTECT, related_name="reservations")
    quantity = models.DecimalField("Miktar", **Q3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name, verbose_name_plural = "Rezervasyon", "Rezervasyonlar"


class StockCount(BaseModel):
    KIND = [("general", "Genel depo sayımı"), ("location", "Raf bazlı sayım"), ("product", "Ürün bazlı sayım")]
    STATUS = [("draft", "Sayılıyor"), ("submitted", "Onay bekliyor"), ("applied", "Uygulandı"),
              ("rejected", "Reddedildi")]

    number = models.CharField("Sayım no", max_length=30, unique=True)
    warehouse = models.ForeignKey(Warehouse, verbose_name="Depo", on_delete=models.PROTECT)
    kind = models.CharField("Sayım türü", max_length=10, choices=KIND, default="general")
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="draft")
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Sayım", "Sayımlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class StockCountLine(models.Model):
    count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    location = models.ForeignKey(Location, verbose_name="Lokasyon", on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, verbose_name="LOT", null=True, blank=True, on_delete=models.PROTECT)
    system_quantity = models.DecimalField("Sistem stoğu", **Q3, default=0)
    counted_quantity = models.DecimalField("Sayılan", **Q3, null=True, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Sayım satırı", "Sayım satırları"

    @property
    def difference(self):
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.system_quantity
