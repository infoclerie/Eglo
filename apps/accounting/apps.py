from django.apps import AppConfig


class AccountingConfig(AppConfig):
    name = "apps.accounting"
    label = "accounting"
    verbose_name = "Finans ve Muhasebe"

    def ready(self):
        from . import handlers  # noqa: F401
