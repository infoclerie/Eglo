import json

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel

from .crypto import decrypt, encrypt


class IntegrationAccount(BaseModel):
    """Bir dış sisteme bağlantı (Uyumsoft, Trendyol, kargo...). Şifreler veritabanında şifreli saklanır."""

    ENV = [("test", "Test ortamı"), ("live", "Canlı ortam")]
    provider = models.CharField("Sağlayıcı", max_length=40, db_index=True)
    name = models.CharField("Bağlantı adı", max_length=100)
    environment = models.CharField("Ortam", max_length=4, choices=ENV, default="test")
    config = models.JSONField("Ayarlar", default=dict, blank=True)
    secret = models.TextField("Gizli bilgiler (şifreli)", blank=True, editable=False)
    active = models.BooleanField("Aktif", default=True)
    last_test_at = models.DateTimeField("Son test", null=True, blank=True)
    last_test_ok = models.BooleanField("Son test başarılı", default=False)
    last_message = models.TextField("Son mesaj", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Entegrasyon bağlantısı", "Entegrasyon bağlantıları"

    def __str__(self):
        return self.name

    def get_secrets(self):
        return json.loads(decrypt(self.secret)) if self.secret else {}

    def set_secrets(self, data):
        self.secret = encrypt(json.dumps(data))

    @property
    def provider_obj(self):
        from .providers import get_provider
        return get_provider(self.provider)


class IntegrationJob(models.Model):
    """Dış sisteme yapılacak her iş kuyruğa yazılır: hata olursa artan aralıklarla yeniden denenir (§13)."""

    STATUS = [("pending", "Bekliyor"), ("running", "Çalışıyor"), ("success", "Başarılı"), ("failed", "Başarısız")]
    account = models.ForeignKey(IntegrationAccount, verbose_name="Bağlantı", on_delete=models.CASCADE, related_name="jobs")
    kind = models.CharField("İş türü", max_length=50)
    ref = models.CharField("Referans", max_length=100, blank=True, db_index=True)
    payload = models.JSONField("Veri", default=dict, blank=True)
    idempotency_key = models.CharField("Tekillik anahtarı", max_length=150, unique=True)
    status = models.CharField("Durum", max_length=8, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField("Deneme", default=0)
    max_attempts = models.PositiveSmallIntegerField("En fazla deneme", default=5)
    next_run_at = models.DateTimeField("Sonraki deneme", default=timezone.now, db_index=True)
    last_error = models.TextField("Son hata", blank=True)
    result = models.JSONField("Sonuç", default=dict, blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    finished_at = models.DateTimeField("Bitiş", null=True, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Entegrasyon işi", "Entegrasyon işleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.ref}"


class SyncLog(models.Model):
    account = models.ForeignKey(IntegrationAccount, on_delete=models.CASCADE, related_name="logs")
    at = models.DateTimeField("Zaman", auto_now_add=True, db_index=True)
    action = models.CharField("İşlem", max_length=60)
    ok = models.BooleanField("Başarılı", default=True)
    message = models.CharField("Mesaj", max_length=500)
    detail = models.TextField("Detay", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Senkronizasyon logu", "Senkronizasyon logları"
        ordering = ["-at"]


class ChannelListing(models.Model):
    """Ürün ↔ pazaryeri eşleştirmesi. Kayıt yoksa ürün barkodu ile eşleşir."""

    account = models.ForeignKey(IntegrationAccount, on_delete=models.CASCADE, related_name="listings")
    product = models.ForeignKey("catalog.Product", verbose_name="Ürün", on_delete=models.CASCADE, related_name="channel_listings")
    external_barcode = models.CharField("Pazaryeri barkodu", max_length=60, blank=True)
    sync_stock = models.BooleanField("Stok/fiyat gönder", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Ürün eşleştirmesi", "Ürün eşleştirmeleri"
        unique_together = [("account", "product")]


class ExternalOrder(models.Model):
    """Pazaryerinden gelen paket/sipariş ham verisi (durum bildirimi için satır kimlikleri burada saklanır)."""

    account = models.ForeignKey(IntegrationAccount, on_delete=models.CASCADE, related_name="external_orders")
    external_id = models.CharField("Paket / sipariş no", max_length=60)
    order = models.OneToOneField("sales.SalesOrder", on_delete=models.CASCADE, related_name="external")
    status = models.CharField("Pazaryeri durumu", max_length=40, blank=True)
    raw = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name, verbose_name_plural = "Pazaryeri siparişi", "Pazaryeri siparişleri"
        unique_together = [("account", "external_id")]
