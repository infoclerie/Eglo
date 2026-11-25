"""
Kritik stok seviyesi kontrolü ve e-posta bildirimi.
Cron / scheduled task olarak çalıştırılır:
  python manage.py check_critical_stock
  python manage.py check_critical_stock --email admin@eglo.com.tr
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Setting
from apps.inventory.services import low_stock_products, expiring_lots


class Command(BaseCommand):
    help = "Kritik stok seviyesinin altındaki ürünleri kontrol eder ve e-posta gönderir."

    def add_arguments(self, parser):
        parser.add_argument("--email", nargs="*", help="Bildirim gönderilecek e-posta adresleri (boş bırakılırsa ayarlardan okunur)")
        parser.add_argument("--dry-run", action="store_true", help="Sadece rapor üret, e-posta gönderme")

    def handle(self, *args, **options):
        now = timezone.localtime()
        low = low_stock_products()
        expiring = expiring_lots(within_days=90)

        if not low and not expiring.exists():
            self.stdout.write(self.style.SUCCESS("Kritik stok yok."))
            return

        # Rapor oluştur
        lines = [f"Eglo ERP — Kritik Stok Raporu ({now:%d.%m.%Y %H:%M})", "=" * 50, ""]

        if low:
            lines.append(f"🔴 Minimum stok altında: {len(low)} ürün")
            lines.append("-" * 40)
            for product, available in low:
                lines.append(f"  {product.sku} — {product.name}")
                lines.append(f"    Mevcut: {available}  |  Minimum: {product.min_stock}  |  Eksik: {product.min_stock - available}")
            lines.append("")

        exp_list = list(expiring[:50])
        if exp_list:
            lines.append(f"⚠️ SKT yaklaşan/geçmiş LOT: {len(exp_list)} adet")
            lines.append("-" * 40)
            for lot in exp_list:
                days = lot.days_to_expiry()
                status = "GEÇMİŞ" if days < 0 else f"{days} gün"
                lines.append(f"  {lot.product.sku} — {lot.product.name}  LOT: {lot.number}")
                lines.append(f"    SKT: {lot.expiry_date:%d.%m.%Y}  |  Kalan: {status}  |  Stok: {lot.on_hand}")
            lines.append("")

        report = "\n".join(lines)
        self.stdout.write(report)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: E-posta gönderilmedi."))
            return

        # E-posta gönder
        recipients = options.get("email") or []
        if not recipients:
            stored = Setting.get("inventory.critical_stock_emails", "")
            if stored:
                recipients = [e.strip() for e in stored.split(",") if e.strip()]

        if not recipients:
            self.stdout.write(self.style.WARNING(
                "E-posta adresi belirtilmedi. --email ile veya "
                "Sistem Ayarları > inventory.critical_stock_emails değeriyle tanımlayın."))
            return

        try:
            from apps.integrations.models import Account
            from apps.integrations.services import enqueue
            email_account = Account.objects.filter(provider__startswith="email", active=True).first()
            if not email_account:
                self.stdout.write(self.style.ERROR("Aktif e-posta entegrasyonu bulunamadı."))
                return
            for to in recipients:
                enqueue(email_account, "notify.email", "critical_stock",
                        {"to": to, "subject": f"Kritik Stok Raporu — {now:%d.%m.%Y}", "body": report},
                        key=f"critical-stock:{now:%Y%m%d}:{to}")
            self.stdout.write(self.style.SUCCESS(f"Rapor {len(recipients)} adrese gönderildi."))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"E-posta gönderilemedi: {exc}"))
