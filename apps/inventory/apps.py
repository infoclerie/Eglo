from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = "apps.inventory"
    label = "inventory"
    verbose_name = "Depo ve Stok"

    def ready(self):
        from . import handlers  # noqa: F401  olay dinleyicilerini kaydeder
