from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models

from .events import EVENTS

EVENT_CHOICES = [(k, v["label"]) for k, v in EVENTS.items()]


class NotificationRule(models.Model):
    """Bildirim merkezi kuralı: hangi olayda, kime, hangi kanaldan, hangi taslakla (müşteri dokümanı §15)."""

    event = models.CharField("Olay", max_length=30, choices=EVENT_CHOICES)
    group = models.ForeignKey(Group, verbose_name="Alıcı rol", null=True, blank=True, on_delete=models.CASCADE,
                              help_text="Personel bildirimlerinde alıcı rol. Boş = yöneticiler. Müşteri bildirimlerinde kullanılmaz.")
    in_app = models.BooleanField("Sistem içi (zil)", default=True)
    email = models.BooleanField("E-posta", default=False)
    sms = models.BooleanField("SMS", default=False)
    subject = models.CharField("E-posta konusu", max_length=200, blank=True)
    body = models.TextField("E-posta metni", blank=True)
    sms_text = models.CharField("SMS metni", max_length=600, blank=True, help_text="SMS 155 karakteri aşarsa birden fazla SMS ücreti alınır.")
    active = models.BooleanField("Aktif", default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Bildirim kuralı", "Bildirim kuralları"
        ordering = ["event"]

    def __str__(self):
        return f"{self.get_event_display()} → {self.recipient_label}"

    @property
    def audience(self):
        return EVENTS.get(self.event, {}).get("audience", "staff")

    @property
    def recipient_label(self):
        return "Müşteri" if self.audience == "customer" else (self.group.name if self.group else "Yöneticiler")


class Notification(models.Model):
    """Sistem içi bildirim (üst çubuktaki zil)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    title = models.CharField("Başlık", max_length=200)
    body = models.TextField("İçerik", blank=True)
    url = models.CharField("Bağlantı", max_length=300, blank=True)
    read = models.BooleanField("Okundu", default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name, verbose_name_plural = "Bildirim", "Bildirimler"
        ordering = ["-created_at"]


class ContactInfo(models.Model):
    """Personelin SMS için cep telefonu."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact")
    mobile = models.CharField("Cep telefonu", max_length=20, blank=True, help_text="5XXXXXXXXX biçiminde. SMS bildirimleri için.")

    class Meta:
        verbose_name, verbose_name_plural = "Personel iletişim bilgisi", "Personel iletişim bilgileri"
