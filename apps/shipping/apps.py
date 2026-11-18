from django.apps import AppConfig


class ShippingConfig(AppConfig):
    name = "apps.shipping"
    label = "shipping"
    verbose_name = "Sevkiyat ve İade"

    def ready(self):
        from . import handlers  # noqa: F401
