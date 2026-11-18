from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Tüm iş modellerinin tabanı: oluşturma/güncelleme zamanı ve oluşturan kullanıcı."""

    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Oluşturan", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", editable=False,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_by_id:
            from .middleware import get_current_user
            user = get_current_user()
            if user is not None:
                self.created_by = user
        super().save(*args, **kwargs)


class Setting(models.Model):
    """Yöneticinin değiştirebileceği sistem parametreleri (ör. SKT uyarı günleri)."""

    key = models.CharField("Anahtar", max_length=100, unique=True)
    value = models.JSONField("Değer")
    description = models.CharField("Açıklama", max_length=255, blank=True)

    class Meta:
        verbose_name = "Sistem ayarı"
        verbose_name_plural = "Sistem ayarları"

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=None):
        obj = cls.objects.filter(key=key).first()
        return obj.value if obj else default

    @classmethod
    def put(cls, key, value, description=""):
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": value, "description": description})
        return obj


class Sequence(models.Model):
    """Belge numarası üretici (SAY-000001, SIP-000001 ...). Kullanım: Sequence.next('count', 'SAY-')"""

    code = models.CharField("Kod", max_length=50, unique=True)
    prefix = models.CharField("Ön ek", max_length=20)
    next_value = models.PositiveBigIntegerField("Sıradaki", default=1)
    padding = models.PositiveSmallIntegerField("Hane", default=6)

    class Meta:
        verbose_name = "Numara serisi"
        verbose_name_plural = "Numara serileri"

    def __str__(self):
        return f"{self.code} ({self.prefix})"

    @classmethod
    def next(cls, code, prefix):
        from django.db import transaction
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(code=code, defaults={"prefix": prefix})
            value = seq.next_value
            seq.next_value += 1
            seq.save(update_fields=["next_value"])
        return f"{seq.prefix}{value:0{seq.padding}d}"


class AuditLog(models.Model):
    """Her kaydın kim tarafından, ne zaman, ne şekilde değiştirildiği (silinemez)."""

    ACTIONS = [("create", "Oluşturma"), ("update", "Güncelleme"), ("delete", "Silme"), ("action", "İşlem")]

    at = models.DateTimeField("Zaman", auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Kullanıcı", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")
    action = models.CharField("İşlem", max_length=10, choices=ACTIONS)
    model = models.CharField("Model", max_length=100, db_index=True)
    object_id = models.CharField("Kayıt no", max_length=64, db_index=True)
    object_repr = models.CharField("Kayıt", max_length=255)
    data = models.JSONField("Veri", default=dict, blank=True)

    class Meta:
        verbose_name = "İşlem logu"
        verbose_name_plural = "İşlem logları"
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.user} {self.action} {self.model}#{self.object_id}"


class ApprovalRequest(models.Model):
    """
    Yönetici onayı gerektiren işlemler (stok düzeltme, fiyat değişikliği, iptal, iade...).
    Onaylandığında `approval.approved.<action>` olayı yayınlanır; işlemi ilgili modül yapar.
    """

    STATUS = [("pending", "Bekliyor"), ("approved", "Onaylandı"), ("rejected", "Reddedildi")]

    action = models.CharField("İşlem kodu", max_length=100, db_index=True)
    title = models.CharField("Başlık", max_length=255)
    target_model = models.CharField("Hedef model", max_length=100)
    target_id = models.CharField("Hedef kayıt", max_length=64)
    payload = models.JSONField("Detay", default=dict, blank=True)
    status = models.CharField("Durum", max_length=10, choices=STATUS, default="pending", db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Talep eden", null=True,
                                     on_delete=models.SET_NULL, related_name="+")
    requested_at = models.DateTimeField("Talep zamanı", auto_now_add=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Karar veren", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField("Karar zamanı", null=True, blank=True)
    note = models.TextField("Not", blank=True)

    class Meta:
        verbose_name = "Onay talebi"
        verbose_name_plural = "Onay talepleri"
        ordering = ["-requested_at"]
        permissions = [("decide_approval", "Onay taleplerini onaylayabilir/reddedebilir")]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class UserPreference(models.Model):
    """Kullanıcıya özel görünüm: menü rengi, ana panel kart sırası ve gizlenen kartlar."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="erp_pref")
    sidebar_color = models.CharField("Menü rengi", max_length=7, blank=True)
    app_order = models.JSONField("Uygulama sırası", default=list, blank=True)
    widget_order = models.JSONField("Kart sırası", default=list, blank=True)
    hidden_widgets = models.JSONField("Gizlenen kartlar", default=list, blank=True)

    class Meta:
        verbose_name, verbose_name_plural = "Kullanıcı tercihi", "Kullanıcı tercihleri"

    @classmethod
    def for_user(cls, user):
        if not getattr(user, "is_authenticated", False):
            return None
        obj, _ = cls.objects.get_or_create(user=user)
        return obj
