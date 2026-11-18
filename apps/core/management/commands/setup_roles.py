from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.core.roles import ROLES


def perms_for(app_label, spec):
    qs = Permission.objects.filter(content_type__app_label=app_label)
    if spec == "all":
        return list(qs)
    if spec == "view":
        return list(qs.filter(codename__startswith="view_"))
    return list(qs.filter(codename__in=spec))


class Command(BaseCommand):
    help = "Rolleri (kullanıcı grupları) ve izinlerini oluşturur/günceller. Tekrar çalıştırılabilir."

    def handle(self, *args, **opts):
        for role, rules in ROLES.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = []
            for app_label, spec in rules.items():
                labels = settings.ERP_MODULES if app_label == "*" else [app_label]
                for label in labels:
                    if label in settings.ERP_MODULES:
                        perms += perms_for(label, spec)
            group.permissions.set(perms)
            self.stdout.write(f"{role}: {len(perms)} izin")
