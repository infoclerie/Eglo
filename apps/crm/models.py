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
