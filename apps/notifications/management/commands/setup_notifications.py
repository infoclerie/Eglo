from django.core.management.base import BaseCommand

from apps.notifications.services import ensure_default_rules


class Command(BaseCommand):
    help = "Bildirim merkezi varsayılan kurallarını ve taslaklarını oluşturur (var olanlara dokunmaz)."

    def handle(self, *args, **opts):
        self.stdout.write(f"{ensure_default_rules()} yeni bildirim kuralı")
