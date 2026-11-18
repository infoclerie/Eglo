from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    name = "apps.purchase"
    label = "purchase"
    verbose_name = "Satın Alma"

    def ready(self):
        from . import handlers  # noqa: F401
