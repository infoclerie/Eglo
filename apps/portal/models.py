from django.conf import settings
from django.db import models

from apps.partners.models import Partner


class PortalAccess(models.Model):
    """Bayi portalı kullanıcısı: bir sistem kullanıcısını bir cari karta bağlar. Bayi sadece kendi carisinin verisini görür."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="Kullanıcı", on_delete=models.CASCADE, related_name="portal")
    partner = models.ForeignKey(Partner, verbose_name="Cari (bayi)", on_delete=models.CASCADE, related_name="portal_users")
    active = models.BooleanField("Aktif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name, verbose_name_plural = "Bayi portal kullanıcısı", "Bayi portal kullanıcıları"

    def __str__(self):
        return f"{self.user.username} → {self.partner.name}"
