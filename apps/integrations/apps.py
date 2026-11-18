from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    name = "apps.integrations"
    label = "integrations"
    verbose_name = "Entegrasyonlar"

    def ready(self):
        from . import handlers  # noqa: F401
