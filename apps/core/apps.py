from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Çekirdek"

    def ready(self):
        from . import audit
        from .registry import check_dependencies
        check_dependencies()
        audit.connect()
