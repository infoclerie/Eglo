from django.conf import settings
from django.db import models

from apps.catalog.models import SalesChannel
from apps.core.models import BaseModel, Sequence

MONEY = dict(max_digits=14, decimal_places=2)


class Partner(BaseModel):
    """Cari kart: müşteri, bayi, tedarikçi, fason üretici (müşteri dokümanı §5.1, §8.2)."""

    KIND = [("customer", "Müşteri"), ("supplier", "Tedarikçi"), ("both", "Müşteri + tedarikçi")]
    GROUP = [
        ("individual", "Bireysel"), ("ecommerce", "E-ticaret müşterisi"), ("pharmacy", "Eczane"),
        ("cosmetic_store", "Kozmetik mağazası"), ("market", "Market"), ("cleaning_seller", "Temizlik ürünleri satıcısı"),
        ("wholesaler", "Toptancı"), ("distributor", "Distribütör"), ("dealer", "Bayi"), ("corporate", "Kurumsal şirket"),
        ("hotel", "Otel / işletme"), ("industry", "Fabrika / sanayi"), ("supplier", "Tedarikçi"),
        ("contract_manufacturer", "Fason üretici"),
    ]

    code = models.CharField("Cari kod", max_length=20, unique=True, blank=True)
    name = models.CharField("Firma / kişi adı", max_length=200)
    kind = models.CharField("Tür", max_length=10, choices=KIND, default="customer")
    group = models.CharField("Grup", max_length=25, choices=GROUP, default="individual")
    contact_person = models.CharField("Yetkili kişi", max_length=100, blank=True)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    email = models.EmailField("E-posta", blank=True)
    tax_office = models.CharField("Vergi dairesi", max_length=100, blank=True)
    tax_number = models.CharField("VKN / TCKN", max_length=11, blank=True, db_index=True)
    e_invoice_user = models.BooleanField("E-fatura mükellefi", default=False)
    address = models.TextField("Fatura adresi", blank=True)
    shipping_address = models.TextField("Teslimat adresi", blank=True)
    city = models.CharField("İl", max_length=50, blank=True)
    district = models.CharField("İlçe", max_length=50, blank=True)
    iban = models.CharField("IBAN", max_length=34, blank=True)
    payment_term_days = models.PositiveIntegerField("Ödeme vadesi (gün)", default=0)
    credit_limit = models.DecimalField("Kredi / risk limiti", **MONEY, default=0, help_text="0 = limit kontrolü yok")
    discount_pct = models.DecimalField("Müşteriye özel indirim %", max_digits=5, decimal_places=2, default=0)
    default_channel = models.ForeignKey(SalesChannel, verbose_name="Fiyat kanalı", null=True, blank=True,
                                        on_delete=models.PROTECT, help_text="Bayi, kurumsal vb. fiyat listesi")
    sales_rep = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Satış temsilcisi", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="+")
    lead_time_days = models.PositiveIntegerField("Teslimat süresi (gün, tedarikçi)", default=0)
    consent_sms = models.BooleanField("SMS izni (İYS)", default=False)
    consent_email = models.BooleanField("E-posta izni (İYS)", default=False)
    consent_date = models.DateTimeField("İzin tarihi", null=True, blank=True)
    note = models.TextField("Not", blank=True)
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Cari kart", "Cari kartlar"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "T-" if self.kind == "supplier" else "C-"
            self.code = Sequence.next(f"partners.{prefix}", prefix)
        super().save(*args, **kwargs)

    @property
    def is_customer(self):
        return self.kind in ("customer", "both")

    @property
    def is_supplier(self):
        return self.kind in ("supplier", "both")
