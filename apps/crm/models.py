from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.partners.models import Partner

MONEY = dict(max_digits=14, decimal_places=2)


class Opportunity(BaseModel):
    """Satış fırsatı (müşteri dokümanı §8.3)."""

    STAGES = [("lead", "Potansiyel müşteri"), ("contacted", "İlk iletişim"), ("needs", "İhtiyaç analizi"),
              ("quoted", "Teklif gönderildi"), ("negotiation", "Pazarlık / takip"), ("won", "Kazanıldı"), ("lost", "Kaybedildi")]
    OPEN = ("lead", "contacted", "needs", "quoted", "negotiation")

    title = models.CharField("Fırsat", max_length=200)
    partner = models.ForeignKey(Partner, verbose_name="Cari", null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities")
    prospect_name = models.CharField("Aday firma / kişi", max_length=200, blank=True)
    contact = models.CharField("İletişim (tel / e-posta)", max_length=200, blank=True)
    stage = models.CharField("Aşama", max_length=12, choices=STAGES, default="lead", db_index=True)
    expected_amount = models.DecimalField("Beklenen aylık ciro", **MONEY, default=0)
    probability = models.PositiveSmallIntegerField("Olasılık %", default=20)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Sorumlu", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    next_action_date = models.DateField("Sonraki adım tarihi", null=True, blank=True)
    lost_reason = models.CharField("Kaybetme nedeni", max_length=200, blank=True)
    stage_changed_at = models.DateTimeField("Aşama zamanı", default=timezone.now)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Satış fırsatı", "Satış fırsatları"
        ordering = ["next_action_date", "-updated_at"]

    def __str__(self):
        return self.title

    @property
    def name(self):
        return self.partner.name if self.partner else self.prospect_name


class Activity(BaseModel):
    """Görüşme, ziyaret, teklif, numune... ve hatırlatmalar (§8.4)."""

    KIND = [("call", "Telefon"), ("email", "E-posta"), ("whatsapp", "WhatsApp"), ("visit", "Ziyaret"), ("meeting", "Toplantı"),
            ("quote", "Teklif"), ("sample", "Numune gönderimi"), ("task", "Takip görevi"), ("note", "Not")]
    kind = models.CharField("Tür", max_length=10, choices=KIND, default="call")
    subject = models.CharField("Konu", max_length=200)
    partner = models.ForeignKey(Partner, verbose_name="Cari", null=True, blank=True, on_delete=models.CASCADE, related_name="activities")
    opportunity = models.ForeignKey(Opportunity, verbose_name="Fırsat", null=True, blank=True, on_delete=models.CASCADE, related_name="activities")
    notes = models.TextField("Görüşme notu", blank=True)
    due_date = models.DateField("Yapılacak tarih (hatırlatma)", null=True, blank=True, db_index=True)
    done = models.BooleanField("Tamamlandı", default=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Sorumlu", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name, verbose_name_plural = "Aktivite / takip", "Aktiviteler / takipler"
        ordering = ["done", "due_date", "-created_at"]

    def __str__(self):
        return self.subject


class Campaign(BaseModel):
    """Toplu e-posta / SMS kampanyası (ticari ileti). Yalnız İYS izni olan carilere gönderilir."""

    CHANNEL = [("email", "E-posta"), ("sms", "SMS")]
    STATUS = [("draft", "Taslak"), ("sent", "Gönderildi")]
    RECIPIENT = [("11", "Bireysel (tüketici)"), ("12", "Tacir / esnaf (bayi, eczane, kurumsal)")]

    name = models.CharField("Kampanya adı", max_length=150, help_text="Yalnız sizin göreceğiniz ad, ör. 'Kasım bayi indirimi'.")
    channel = models.CharField("Kanal", max_length=5, choices=CHANNEL, default="email")
    segments = models.JSONField("Segmentler", default=list, blank=True,
                                help_text="Boş = tüm müşteriler. VIP, düzenli, yeni, uzun süredir almayan...")
    city = models.CharField("İl filtresi", max_length=50, blank=True, help_text="Boş = tüm iller.")
    recipient_type = models.CharField("Alıcı türü (İYS)", max_length=2, choices=RECIPIENT, default="12",
                                      help_text="İYS'de izin bireysel ve tacir olarak ayrı tutulur.")
    subject = models.CharField("E-posta konusu", max_length=200, blank=True)
    body = models.TextField("Mesaj", help_text="{musteri}, {cari_kodu}, {firma} yazabilirsiniz; gönderimde doldurulur.")
    status = models.CharField("Durum", max_length=6, choices=STATUS, default="draft")
    sent_at = models.DateTimeField("Gönderim zamanı", null=True, blank=True)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Gönderen", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    queued = models.PositiveIntegerField("Kuyruğa alınan", default=0)
    skipped = models.PositiveIntegerField("Atlanan (izin / iletişim yok)", default=0)

    class Meta:
        verbose_name, verbose_name_plural = "Kampanya", "Kampanyalar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CampaignRecipient(models.Model):
    STATUS = [("queued", "Gönderim kuyruğunda"), ("no_consent", "İYS izni yok"), ("no_contact", "E-posta / cep yok")]
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="+")
    to = models.CharField("Alıcı", max_length=200, blank=True)
    status = models.CharField("Durum", max_length=10, choices=STATUS)

    class Meta:
        verbose_name, verbose_name_plural = "Kampanya alıcısı", "Kampanya alıcıları"
        unique_together = [("campaign", "partner")]
