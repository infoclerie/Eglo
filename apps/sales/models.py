from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Product, SalesChannel
from apps.core.models import BaseModel
from apps.inventory.models import Warehouse
from apps.partners.models import Partner

MONEY = dict(max_digits=14, decimal_places=2)
Q3 = dict(max_digits=14, decimal_places=3)
CENT = Decimal("0.01")


class SalesOrder(BaseModel):
    STATUS = [
        ("new", "Yeni sipariş"), ("awaiting_payment", "Ödeme bekliyor"), ("payment_ok", "Ödeme onaylandı"),
        ("reserved", "Stok rezerve edildi"), ("picking", "Toplama başladı"), ("picked", "Toplama tamamlandı"),
        ("packed", "Paketlendi / sevkiyata hazır"), ("invoiced", "Fatura oluşturuldu"),
        ("shipped", "Kargoya teslim edildi"), ("delivered", "Teslim edildi"), ("cancelled", "İptal edildi"),
        ("return_requested", "İade talebi açıldı"), ("returned", "İade tamamlandı"),
    ]
    PAYMENT = [("card", "Kredi kartı"), ("transfer", "Havale / EFT"), ("cash", "Nakit"), ("term", "Vadeli (cari)"),
               ("marketplace", "Pazaryeri tahsilatı"), ("cod", "Kapıda ödeme")]
    EDITABLE = {"new", "awaiting_payment", "payment_ok"}

    number = models.CharField("Sipariş no", max_length=30, unique=True)
    order_date = models.DateTimeField("Sipariş tarihi", default=timezone.now, db_index=True)
    channel = models.ForeignKey(SalesChannel, verbose_name="Satış kanalı", on_delete=models.PROTECT)
    external_ref = models.CharField("Kanal sipariş no", max_length=60, blank=True,
                                    help_text="Trendyol/HB/Amazon sipariş numarası — mükerrer kayıt engeli")
    customer = models.ForeignKey(Partner, verbose_name="Cari", null=True, blank=True, on_delete=models.PROTECT,
                                 related_name="sales_orders")
    customer_name = models.CharField("Müşteri adı", max_length=200, blank=True)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    email = models.EmailField("E-posta", blank=True)
    shipping_address = models.TextField("Teslimat adresi", blank=True)
    billing_address = models.TextField("Fatura adresi", blank=True)
    tax_number = models.CharField("VKN / TCKN", max_length=11, blank=True)
    warehouse = models.ForeignKey(Warehouse, verbose_name="Çıkış deposu", null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField("Durum", max_length=20, choices=STATUS, default="new", db_index=True)
    status_changed_at = models.DateTimeField("Durum zamanı", default=timezone.now)
    payment_method = models.CharField("Ödeme şekli", max_length=12, choices=PAYMENT, default="card")
    credit_approved = models.BooleanField("Limit aşımı onaylı", default=False, editable=False)
    coupon_code = models.CharField("Kupon", max_length=40, blank=True)
    subtotal = models.DecimalField("Ara toplam (KDV hariç)", **MONEY, default=0)
    discount_total = models.DecimalField("İndirim", **MONEY, default=0)
    shipping_fee = models.DecimalField("Kargo bedeli (KDV hariç)", **MONEY, default=0)
    vat_total = models.DecimalField("KDV", **MONEY, default=0)
    grand_total = models.DecimalField("Genel toplam", **MONEY, default=0)
    applied_campaigns = models.CharField("Uygulanan kampanyalar", max_length=255, blank=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Satış siparişi", "Satış siparişleri"
        ordering = ["-order_date"]
        constraints = [models.UniqueConstraint(fields=["channel", "external_ref"], condition=~Q(external_ref=""),
                                               name="uniq_channel_external_ref")]

    def __str__(self):
        return self.number

    @property
    def display_customer(self):
        return self.customer.name if self.customer else self.customer_name

    @property
    def hours_in_status(self):
        return round((timezone.now() - self.status_changed_at).total_seconds() / 3600, 1)


class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", on_delete=models.PROTECT)
    quantity = models.DecimalField("Miktar", **Q3)
    unit_price = models.DecimalField("Birim fiyat (KDV hariç)", **MONEY, null=True, blank=True,
                                     help_text="Boş bırakılırsa kanal/müşteri fiyatı kullanılır")
    discount = models.DecimalField("Satır indirimi", **MONEY, default=0)
    order_discount_share = models.DecimalField("Sepet indirimi payı", **MONEY, default=0, editable=False)
    vat_rate = models.DecimalField("KDV %", max_digits=5, decimal_places=2, null=True, blank=True)
    vat_amount = models.DecimalField("KDV tutarı", **MONEY, default=0, editable=False)

    class Meta:
        verbose_name, verbose_name_plural = "Sipariş satırı", "Sipariş satırları"

    def __str__(self):
        return f"{self.product.sku} × {self.quantity}"

    @property
    def gross(self):
        return (self.quantity * (self.unit_price or 0)).quantize(CENT)

    @property
    def net(self):
        """KDV hariç, tüm indirimler düşülmüş satır tutarı."""
        return self.gross - self.discount - self.order_discount_share


class Campaign(BaseModel):
    KIND = [
        ("cart_percent", "Sepette % indirim"),
        ("buy_x_pay_y", "X al Y öde (3 al 2 öde, 1 alana 1 bedava = 2 al 1 öde)"),
        ("nth_item_price", "N. ürün sabit fiyat (ikinci ürün 1 TL)"),
        ("free_shipping_over", "Belirli tutar üzeri ücretsiz kargo"),
        ("coupon_percent", "Kupon ile % indirim"),
    ]
    name = models.CharField("Kampanya", max_length=150)
    kind = models.CharField("Tür", max_length=20, choices=KIND)
    channels = models.ManyToManyField(SalesChannel, verbose_name="Geçerli kanallar", blank=True,
                                      help_text="Boş = tüm kanallar")
    products = models.ManyToManyField(Product, verbose_name="Geçerli ürünler", blank=True, related_name="+",
                                      help_text="Boş = tüm ürünler (ürün bazlı kampanyalar için)")
    starts_at = models.DateTimeField("Başlangıç")
    ends_at = models.DateTimeField("Bitiş")
    x = models.PositiveIntegerField("X / N", default=0, help_text="X al Y öde: X; N. ürün: N")
    y = models.PositiveIntegerField("Y", default=0)
    percent = models.DecimalField("İndirim %", max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField("Tutar", **MONEY, default=0, help_text="N. ürün fiyatı")
    min_amount = models.DecimalField("Minimum sepet tutarı", **MONEY, default=0)
    max_discount = models.DecimalField("Maksimum indirim", **MONEY, default=0, help_text="0 = sınırsız")
    coupon_code = models.CharField("Kupon kodu", max_length=40, blank=True, db_index=True)
    max_uses = models.PositiveIntegerField("Maksimum kullanım", default=0, help_text="0 = sınırsız")
    used_count = models.PositiveIntegerField("Kullanım", default=0, editable=False)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Kampanya", "Kampanyalar"
        ordering = ["-starts_at"]

    def __str__(self):
        return self.name


class OrderStatusLog(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="status_logs")
    status = models.CharField("Durum", max_length=20, choices=SalesOrder.STATUS)
    at = models.DateTimeField("Zaman", default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField("Not", max_length=255, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Durum geçmişi", "Durum geçmişi"
        ordering = ["at"]
