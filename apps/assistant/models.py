from django.conf import settings
from django.db import models


class AssistantMessage(models.Model):
    """Asistan konuşma geçmişi (kullanıcı başına) ve kullanım ölçümü. 'add' izni = asistanı kullanabilir."""

    ROLE = [("user", "Soru"), ("assistant", "Cevap")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Kullanıcı", on_delete=models.CASCADE, related_name="+")
    role = models.CharField("Tür", max_length=10, choices=ROLE)
    content = models.TextField("Metin")
    tools_used = models.JSONField("Kullanılan veri sorguları", default=list, blank=True)
    tokens_in = models.PositiveIntegerField("Giden token", default=0)
    tokens_out = models.PositiveIntegerField("Gelen token", default=0)
    provider = models.CharField("Servis", max_length=40, blank=True)
    created_at = models.DateTimeField("Zaman", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name, verbose_name_plural = "Asistan mesajı", "Asistan mesajları"
        ordering = ["created_at"]
        permissions = [("view_all_usage", "Tüm kullanıcıların asistan kullanımını görebilir")]

    def __str__(self):
        return f"{self.user} · {self.get_role_display()} · {self.content[:40]}"
