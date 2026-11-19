from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.backups import read_meta, restore_backup


class Command(BaseCommand):
    help = "Yedek dosyasından (.zip) sistemi geri yükler. Yeni sunucuya taşımada kullanılır. TÜM mevcut verinin yerine geçer."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Yedek dosyasının yolu (.zip)")
        parser.add_argument("--yes", action="store_true", help="Onay sormadan uygula")

    def handle(self, *args, **opts):
        try:
            meta = read_meta(opts["path"])
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))
        self.stdout.write(f"Yedek: {meta.get('name')} · {meta.get('created_at')} · {meta.get('records')} kayıt · {meta['photos']} fotoğraf")
        if not opts["yes"] and input("Mevcut tüm veri bu yedekle değiştirilecek. Devam? (evet/hayır): ").strip().lower() != "evet":
            raise CommandError("İptal edildi.")
        try:
            res = restore_backup(path=opts["path"], safety_backup=True)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))
        for w in res["warnings"]:
            self.stdout.write(self.style.WARNING(w))
        self.stdout.write(self.style.SUCCESS("Geri yükleme tamamlandı. Eski kullanıcı adı ve şifrelerle giriş yapabilirsiniz."))
