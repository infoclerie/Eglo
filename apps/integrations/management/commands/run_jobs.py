import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.integrations.services import run_due, schedule_periodic


class Command(BaseCommand):
    help = "Entegrasyon iş kuyruğunu çalıştırır. --loop ile sürekli (arka plan işçisi)."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--interval", type=int, default=20)

    def handle(self, *args, loop=False, interval=20, **opts):
        while True:
            close_old_connections()
            try:
                schedule_periodic()
                n = run_due()
                if n:
                    self.stdout.write(f"{n} iş çalıştırıldı")
            except Exception as exc:  # noqa: BLE001 — işçi asla durmamalı
                self.stderr.write(f"İşçi hatası: {exc}")
            if not loop:
                break
            time.sleep(interval)
