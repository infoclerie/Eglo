from django.db import models


class ImportPermission(models.Model):
    """Veri tutmaz; yalnız 'toplu yükleme yapabilir' izni için (imports.add_importpermission)."""

    class Meta:
        managed = False
        default_permissions = ("add",)
        verbose_name, verbose_name_plural = "Toplu yükleme", "Toplu yükleme"
