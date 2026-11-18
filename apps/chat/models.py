from django.conf import settings
from django.db import models
from django.utils import timezone

ONLINE_SECONDS = 60  # son 60 sn içinde sinyal gönderen kullanıcı "çevrimiçi" (yeşil)


class Conversation(models.Model):
    KIND = [("direct", "Birebir"), ("group", "Grup"), ("support", "Müşteri / bayi destek")]
    kind = models.CharField("Tür", max_length=8, choices=KIND, default="direct")
    title = models.CharField("Başlık", max_length=150, blank=True)
    partner = models.ForeignKey("partners.Partner", verbose_name="Cari", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name, verbose_name_plural = "Sohbet", "Sohbetler"
        ordering = ["-updated_at"]


class Participant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_participations")
    last_read_id = models.BigIntegerField(default=0)

    class Meta:
        unique_together = [("conversation", "user")]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name, verbose_name_plural = "Mesaj", "Mesajlar"
        ordering = ["id"]


class Presence(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence")
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)

    @property
    def online(self):
        return (timezone.now() - self.last_seen).total_seconds() < ONLINE_SECONDS
