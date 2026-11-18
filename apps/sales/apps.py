from django.apps import AppConfig


class SalesConfig(AppConfig):
    name = "apps.sales"
    label = "sales"
    verbose_name = "Sipariş Yönetimi"

    def ready(self):
        from . import handlers  # noqa: F401
