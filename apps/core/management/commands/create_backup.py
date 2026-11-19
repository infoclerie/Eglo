from django.core.management.base import BaseCommand

from apps.core.backups import create_backup, root


class Command(BaseCommand):
    help = "Tam yedek alır (veritabanı + ürün fotoğrafları) → BACKUP_ROOT altında .zip"

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Komut satırı yedeği")

    def handle(self, *args, **opts):
        name = create_backup(opts["name"], kind="manual")
        self.stdout.write(self.style.SUCCESS(f"Yedek alındı: {root() / name}"))
