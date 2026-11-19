from django.apps import AppConfig


class ProductionConfig(AppConfig):
    name = "apps.production"
    label = "production"
    verbose_name = "Üretim ve Fason"

    def ready(self):
        from . import handlers  # noqa: F401
