from django.core.management.base import BaseCommand

from apps.core.context_pack import build_pack


class Command(BaseCommand):
    help = "Yapay zekâ için proje rehberini üretir (varsayılan: PROJE_REHBERI_AI.md). --no-live: canlı veri özeti olmadan (GitHub için)."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="PROJE_REHBERI_AI.md")
        parser.add_argument("--no-live", action="store_true")

    def handle(self, *args, **o):
        open(o["out"], "w", encoding="utf-8").write(build_pack(include_live=not o["no_live"]))
        self.stdout.write(self.style.SUCCESS(f"Yazıldı: {o['out']}"))
