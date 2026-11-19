from django.db import models


class Report(models.Model):
    """Veri tutmaz; yalnız rapor görme izni için (reports.view_report)."""

    class Meta:
        managed = False
        default_permissions = ("view",)
        verbose_name, verbose_name_plural = "Rapor", "Raporlar"
