import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, SalesChannel
from apps.core.models import BaseModel
from apps.partners.models import Partner

MONEY = dict(max_digits=14, decimal_places=2)
Q3 = dict(max_digits=14, decimal_places=3)
ZERO = Decimal("0")


class Account(BaseModel):
    """Kasa, banka, POS veya pazaryeri hesabı (§9.5)."""

    KIND = [("cash", "Kasa"), ("bank", "Banka"), ("pos", "POS"), ("marketplace", "Pazaryeri hesabı")]
    name = models.CharField("Hesap adı", max_length=100)
    kind = models.CharField("Tür", max_length=12, choices=KIND)
    iban = models.CharField("IBAN", max_length=34, blank=True)
    currency = models.CharField("Para birimi", max_length=3, default="TRY")
    channel = models.ForeignKey(SalesChannel, verbose_name="Pazaryeri", null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Kasa / banka hesabı", "Kasa / banka hesapları"

    def __str__(self):
        return self.name


class Invoice(BaseModel):
    DIRECTION = [("out", "Giden (satış)"), ("in", "Gelen (alış)")]
    KIND = [("sale", "Satış faturası"), ("sale_return", "Satış iade faturası"), ("purchase", "Alış faturası"),
            ("purchase_return", "Alış iade faturası")]
    DOC = [("efatura", "e-Fatura"), ("earsiv", "e-Arşiv"), ("paper", "Kâğıt / diğer")]
    PROFILE = [("TEMELFATURA", "Temel fatura"), ("TICARIFATURA", "Ticari fatura"), ("EARSIVFATURA", "e-Arşiv fatura")]
    STATUS = [("draft", "Taslak"), ("ready", "Gönderime hazır"), ("queued", "Kuyrukta"), ("sent", "Gönderildi"),
              ("accepted", "Kabul edildi"), ("rejected", "Reddedildi"), ("error", "Hata"), ("on_hold", "Onay bekliyor (uyuşmazlık)"),
              ("posted", "Kaydedildi"), ("cancelled", "İptal")]

    direction = models.CharField("Yön", max_length=3, choices=DIRECTION, default="out")
    kind = models.CharField("Tür", max_length=16, choices=KIND, default="sale")
    doc_type = models.CharField("Belge tipi", max_length=8, choices=DOC, default="earsiv")
    profile = models.CharField("Senaryo", max_length=14, choices=PROFILE, default="EARSIVFATURA")
    number = models.CharField("Fatura no", max_length=30, blank=True, db_index=True)
    uuid = models.UUIDField("ETTN", default=uuid.uuid4, unique=True)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="draft", db_index=True)
    partner = models.ForeignKey(Partner, verbose_name="Cari", null=True, blank=True, on_delete=models.PROTECT, related_name="invoices")
    buyer_title = models.CharField("Unvan / ad soyad", max_length=200, blank=True)
    buyer_vkn = models.CharField("VKN / TCKN", max_length=11, blank=True)
    buyer_tax_office = models.CharField("Vergi dairesi", max_length=100, blank=True)
    buyer_address = models.TextField("Adres", blank=True)
    buyer_city = models.CharField("İl", max_length=50, blank=True)
    buyer_district = models.CharField("İlçe", max_length=50, blank=True)
    buyer_email = models.EmailField("E-posta", blank=True)
    buyer_alias = models.CharField("Alıcı posta kutusu (etiket)", max_length=120, blank=True)
    issue_date = models.DateField("Fatura tarihi", default=timezone.localdate)
    due_date = models.DateField("Vade tarihi", null=True, blank=True)
    currency = models.CharField("Para birimi", max_length=3, default="TRY")
    subtotal = models.DecimalField("Mal/hizmet toplamı (KDV hariç)", **MONEY, default=0)
    vat_total = models.DecimalField("KDV", **MONEY, default=0)
    total = models.DecimalField("Ödenecek tutar", **MONEY, default=0)
    sales_order = models.ForeignKey("sales.SalesOrder", verbose_name="Sipariş", null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="invoices")
    purchase_order = models.ForeignKey("purchase.PurchaseOrder", verbose_name="Satın alma siparişi", null=True, blank=True,
                                       on_delete=models.PROTECT, related_name="invoices")
    original = models.ForeignKey("self", verbose_name="İade edilen fatura", null=True, blank=True, on_delete=models.PROTECT)
    source = models.CharField("Kaynak", max_length=12, default="system", choices=[("system", "Sistem"), ("integrator", "Entegratör")])
    external_status = models.CharField("Entegratör durumu", max_length=100, blank=True)
    message = models.TextField("Mesaj / hata", blank=True)
    xml = models.TextField("UBL XML", blank=True)
    raw = models.JSONField("Entegratör ham verisi", default=dict, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Fatura", "Faturalar"
        ordering = ["-issue_date", "-id"]
        constraints = [models.UniqueConstraint(fields=["direction", "number"], condition=~models.Q(number=""),
                                               name="uniq_invoice_direction_number")]

    def __str__(self):
        return self.number or f"Taslak #{self.pk}"

    @property
    def paid_amount(self):
        return self.payments.aggregate(s=models.Sum("amount"))["s"] or ZERO

    @property
    def open_amount(self):
        return self.total - self.paid_amount


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="Ürün", null=True, blank=True, on_delete=models.PROTECT)
    description = models.CharField("Açıklama", max_length=255)
    quantity = models.DecimalField("Miktar", **Q3)
    unit_code = models.CharField("Birim (UBL)", max_length=5, default="C62", help_text="C62 adet, KGM kg, LTR litre")
    unit_price = models.DecimalField("Birim fiyat (KDV hariç, indirimli)", max_digits=14, decimal_places=4)
    vat_rate = models.DecimalField("KDV %", max_digits=5, decimal_places=2)
    net_amount = models.DecimalField("Tutar (KDV hariç)", **MONEY)
    vat_amount = models.DecimalField("KDV tutarı", **MONEY)
    po_line = models.ForeignKey("purchase.PurchaseOrderLine", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.description} × {self.quantity.normalize():f}"

    class Meta:
        verbose_name, verbose_name_plural = "Fatura satırı", "Fatura satırları"


class Payment(BaseModel):
    DIRECTION = [("in", "Tahsilat"), ("out", "Ödeme")]
    METHOD = [("cash", "Nakit"), ("transfer", "Havale / EFT"), ("card", "Kredi kartı"), ("pos", "POS"),
              ("marketplace", "Pazaryeri hakedişi"), ("check", "Çek / senet")]
    direction = models.CharField("Yön", max_length=3, choices=DIRECTION)
    partner = models.ForeignKey(Partner, verbose_name="Cari", on_delete=models.PROTECT, related_name="payments")
    account = models.ForeignKey(Account, verbose_name="Hesap", on_delete=models.PROTECT)
    amount = models.DecimalField("Tutar", **MONEY)
    date = models.DateField("Tarih", default=timezone.localdate)
    method = models.CharField("Yöntem", max_length=12, choices=METHOD, default="transfer")
    invoice = models.ForeignKey(Invoice, verbose_name="Fatura", null=True, blank=True, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField("Dekont / referans", max_length=100, blank=True)
    fee = models.DecimalField("Banka / POS masrafı", **MONEY, default=0)

    class Meta:
        verbose_name, verbose_name_plural = "Tahsilat / ödeme", "Tahsilatlar / ödemeler"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_direction_display()} {self.partner.name} {self.amount}"


class LedgerEntry(models.Model):
    """Cari hesap hareketi. Bakiye = Σ borç − Σ alacak (pozitif: cari bize borçlu)."""

    DOC = [("opening", "Açılış"), ("invoice", "Fatura"), ("payment", "Tahsilat/ödeme"), ("adjust", "Düzeltme"),
           ("cancel", "İptal")]
    partner = models.ForeignKey(Partner, verbose_name="Cari", on_delete=models.PROTECT, related_name="ledger")
    date = models.DateField("Tarih", db_index=True)
    due_date = models.DateField("Vade", null=True, blank=True)
    doc_type = models.CharField("Belge", max_length=10, choices=DOC)
    description = models.CharField("Açıklama", max_length=255)
    debit = models.DecimalField("Borç", **MONEY, default=0)
    credit = models.DecimalField("Alacak", **MONEY, default=0)
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name, verbose_name_plural = "Cari hareket", "Cari hareketler"
        ordering = ["date", "id"]


class ChannelCostProfile(models.Model):
    """Kanal bazında değişken maliyetler (kârlılık ve hakediş tahmini için)."""

    channel = models.OneToOneField(SalesChannel, verbose_name="Kanal", on_delete=models.CASCADE, related_name="cost_profile")
    commission_pct = models.DecimalField("Komisyon %", max_digits=5, decimal_places=2, default=0)
    shipping_cost_per_order = models.DecimalField("Sipariş başı kargo gideri", **MONEY, default=0)
    service_fee_per_order = models.DecimalField("Sipariş başı hizmet bedeli", **MONEY, default=0)
    ad_cost_pct = models.DecimalField("Reklam gideri % (ciroya)", max_digits=5, decimal_places=2, default=0)
    pos_commission_pct = models.DecimalField("POS komisyonu % (kartlı satış)", max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name, verbose_name_plural = "Kanal maliyet profili", "Kanal maliyet profilleri"

    def __str__(self):
        return str(self.channel)


class ProductCostExtra(models.Model):
    """Ürün başı ek değişken maliyet (ambalaj, etiket, depolama) — gerçek kârlılık için."""

    product = models.OneToOneField(Product, verbose_name="Ürün", on_delete=models.CASCADE, related_name="cost_extra")
    packaging_cost = models.DecimalField("Ambalaj / etiket maliyeti", **MONEY, default=0)
    storage_cost = models.DecimalField("Depolama maliyeti", **MONEY, default=0)
    other_cost = models.DecimalField("Diğer değişken maliyet", **MONEY, default=0)

    class Meta:
        verbose_name, verbose_name_plural = "Ürün ek maliyeti", "Ürün ek maliyetleri"


class MarketplaceSettlement(BaseModel):
    """Pazaryeri hakediş mutabakatı (§9.6): rapor tutarları ile bankaya yatan karşılaştırılır."""

    STATUS = [("open", "Açık"), ("matched", "Eşleşti"), ("mismatch", "Fark var")]
    channel = models.ForeignKey(SalesChannel, verbose_name="Pazaryeri", on_delete=models.PROTECT)
    period_start = models.DateField("Dönem başı")
    period_end = models.DateField("Dönem sonu")
    gross_sales = models.DecimalField("Ürün satış tutarı", **MONEY, default=0)
    commission = models.DecimalField("Komisyon", **MONEY, default=0)
    shipping = models.DecimalField("Kargo kesintisi", **MONEY, default=0)
    ads = models.DecimalField("Reklam", **MONEY, default=0)
    campaign_share = models.DecimalField("Kampanya katkı payı", **MONEY, default=0)
    returns = models.DecimalField("İade / iptal kesintisi", **MONEY, default=0)
    service_fees = models.DecimalField("Hizmet bedelleri / diğer", **MONEY, default=0)
    bank_received = models.DecimalField("Bankaya yatan", **MONEY, default=0)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="open")
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Pazaryeri hakedişi", "Pazaryeri hakedişleri"
        ordering = ["-period_end"]

    def __str__(self):
        return f"{self.channel} {self.period_start:%d.%m}–{self.period_end:%d.%m.%Y}"

    @property
    def expected_net(self):
        return (self.gross_sales - self.commission - self.shipping - self.ads - self.campaign_share
                - self.returns - self.service_fees)

    @property
    def difference(self):
        return self.bank_received - self.expected_net
