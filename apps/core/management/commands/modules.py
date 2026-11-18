from django.core.management.base import BaseCommand

from apps.core.registry import check_dependencies


class Command(BaseCommand):
    help = "Açık ERP modüllerini, sürümlerini ve bağımlılıklarını listeler."

    def handle(self, *args, **opts):
        for code, m in check_dependencies().items():
            deps = ", ".join(m.get("depends", [])) or "-"
            self.stdout.write(f"{code:12} {m['version']:8} {m['name']:25} bağımlı: {deps}")
