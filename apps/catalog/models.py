from django.conf import settings
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel

Q3 = dict(max_digits=14, decimal_places=3)
MONEY = dict(max_digits=14, decimal_places=2)


class Brand(BaseModel):
    name = models.CharField("Marka", max_length=100, unique=True)

    class Meta:
        verbose_name, verbose_name_plural = "Marka", "Markalar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(BaseModel):
    name = models.CharField("Kategori", max_length=100)
    parent = models.ForeignKey("self", verbose_name="Üst kategori", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="children")

    class Meta:
        verbose_name, verbose_name_plural = "Kategori", "Kategoriler"
        unique_together = [("parent", "name")]
        ordering = ["parent__name", "name"]

    def __str__(self):
        return f"{self.parent} / {self.name}" if self.parent else self.name


class SalesChannel(BaseModel):
    """Satış kanalı: Trendyol, Hepsiburada, Amazon, Web, Bayi, Kurumsal, Eczane, Telefon..."""

    code = models.SlugField("Kod", max_length=30, unique=True)
    name = models.CharField("Kanal", max_length=100)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Satış kanalı", "Satış kanalları"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(BaseModel):
    KIND = [("standard", "Standart ürün"), ("kit", "Set / kampanya paketi"),
            ("raw", "Hammadde"), ("packaging", "Ambalaj / etiket / koli")]
    UNIT = [("pcs", "Adet"), ("case", "Koli"), ("l", "Litre"), ("kg", "Kg")]
    GROUP = [("cosmetic", "Kozmetik"), ("liquid_cleaning", "Sıvı temizlik"), ("spray", "Sprey"),
             ("concentrate", "Konsantre"), ("sample", "Numune / tester"), ("promo", "Promosyon / hediye"),
             ("set", "Set / kampanya"), ("other", "Diğer")]

    sku = models.CharField("Ürün kodu (SKU)", max_length=50, unique=True)
    barcode = models.CharField("Barkod (EAN/GTIN)", max_length=32, unique=True, null=True, blank=True)
    name = models.CharField("Ürün adı", max_length=200)
    brand = models.ForeignKey(Brand, verbose_name="Marka", null=True, blank=True, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, verbose_name="Kategori", null=True, blank=True, on_delete=models.PROTECT)
    group = models.CharField("Ürün grubu", max_length=20, choices=GROUP, default="other")
    kind = models.CharField("Tür", max_length=10, choices=KIND, default="standard")
    description = models.TextField("Açıklama", blank=True)
    unit = models.CharField("Birim", max_length=5, choices=UNIT, default="pcs")
    volume = models.CharField("Hacim / ağırlık", max_length=30, blank=True, help_text="100 ml, 3 L ...")
    weight_kg = models.DecimalField("Birim ağırlık (kg)", **Q3, default=0)
    units_per_case = models.PositiveIntegerField("Koli içi adet", default=1)
    case_barcode = models.CharField("Koli barkodu", max_length=32, unique=True, null=True, blank=True)
    cases_per_pallet = models.PositiveIntegerField("Palet başına koli", default=0)
    cost = models.DecimalField("Alış / üretim maliyeti", **MONEY, default=0)
    list_price = models.DecimalField("Liste satış fiyatı (KDV hariç)", **MONEY, default=0)
    vat_rate = models.DecimalField("KDV %", max_digits=5, decimal_places=2, default=Decimal("20"))
    min_stock = models.DecimalField("Minimum stok", **Q3, default=0)
    max_stock = models.DecimalField("Maksimum stok", **Q3, default=0)
    safety_stock = models.DecimalField("Güvenlik stoğu", **Q3, default=0)
    lead_time_days = models.PositiveIntegerField("Tedarik süresi (gün)", default=0)
    track_lot = models.BooleanField("LOT / SKT takibi", default=True)
    shelf_life_days = models.PositiveIntegerField("Raf ömrü (gün)", default=0)
    storage_condition = models.CharField("Depolama koşulu", max_length=200, blank=True)
    image_url = models.CharField("Görsel yolu / URL", max_length=255, blank=True)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Ürün", "Ürünler"
        ordering = ["sku"]

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    @property
    def is_kit(self):
        return self.kind == "kit"

    @property
    def main_image(self):
        """Ana fotoğraf (yoksa en son yüklenen) — ProductImage veya None."""
        imgs = getattr(self, "_prefetched_objects_cache", {}).get("images")
        if imgs is not None:
            imgs = list(imgs)
            return next((i for i in imgs if i.is_main), imgs[0] if imgs else None)
        return self.images.order_by("-is_main", "-created_at").first()

    def price_for(self, channel):
        p = self.prices.filter(channel=channel).first()
        return p.price if p else self.list_price


class ProductPrice(BaseModel):
    """Kanal bazında satış fiyatı (KDV hariç)."""

    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.CASCADE, related_name="prices")
    channel = models.ForeignKey(SalesChannel, verbose_name="Kanal", on_delete=models.PROTECT)
    price = models.DecimalField("Fiyat", **MONEY)

    class Meta:
        verbose_name, verbose_name_plural = "Kanal fiyatı", "Kanal fiyatları"
        unique_together = [("product", "channel")]


class KitComponent(BaseModel):
    """Set içeriği. Set satıldığında stok bu bileşenlerden düşer."""

    kit = models.ForeignKey(Product, verbose_name="Set", on_delete=models.CASCADE, related_name="components")
    component = models.ForeignKey(Product, verbose_name="Bileşen", on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField("Miktar", **Q3, default=1)

    class Meta:
        verbose_name, verbose_name_plural = "Set bileşeni", "Set bileşenleri"
        unique_together = [("kit", "component")]

    def clean(self):
        if self.kit_id == self.component_id:
            raise ValidationError("Bir set kendisini içeremez.")
        if self.component_id and self.component.is_kit:
            raise ValidationError("Set içine başka bir set eklenemez.")
        if self.quantity <= 0:
            raise ValidationError("Miktar sıfırdan büyük olmalı.")


class ProductImage(models.Model):
    """Ürün fotoğrafı (mal kabulde telefondan çekilebilir). Yüklenen görsel küçültülür; küçük önizleme ayrıca tutulur."""

    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("Fotoğraf", upload_to="urunler/%Y/%m/")
    thumb = models.ImageField("Önizleme", upload_to="urunler/kucuk/%Y/%m/", blank=True)
    is_main = models.BooleanField("Ana görsel", default=False, help_text="Listelerde ve bayi portalında görünen fotoğraf.")
    note = models.CharField("Not", max_length=150, blank=True, help_text="Ör. mal kabul SAS-000012, ön yüz, koli görünümü.")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Yükleyen", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("Yükleme zamanı", auto_now_add=True)

    class Meta:
        verbose_name, verbose_name_plural = "Ürün fotoğrafı", "Ürün fotoğrafları"
        ordering = ["-is_main", "-created_at"]

    def __str__(self):
        return f"{self.product.sku} fotoğraf"
