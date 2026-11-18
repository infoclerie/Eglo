from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Bildirimler"

    def ready(self):
        from . import handlers
        handlers.connect()
