import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from PIL import Image

from apps.catalog import services as catalog
from apps.core import backups as bk
from apps.core.testing.fixtures import ErpFixture
from apps.integrations.models import IntegrationAccount, IntegrationJob
from apps.inventory import services as inventory
from apps.sales import services as sales
from apps.sales.models import SalesOrder

TMP = tempfile.mkdtemp()


def jpg():
    buf = BytesIO()
    Image.new("RGB", (50, 50), "red").save(buf, "JPEG")
    return SimpleUploadedFile("a.jpg", buf.getvalue())


@override_settings(MEDIA_ROOT=TMP + "/media", BACKUP_ROOT=TMP + "/bk")
class BackupTests(ErpFixture, TransactionTestCase):
    """TransactionTestCase: geri yükleme veritabanını boşaltıp yeniden doldurur."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_backup_restore_roundtrip_with_photos(self):
        catalog.add_image(self.serum, jpg())
        r = self.client.post("/ayarlar/yedekler/", {"action": "create", "name": "Test öncesi temiz"})
        self.assertEqual(r.status_code, 302)
        b = bk.list_backups()[0]
        self.assertEqual((b["name"], b["photos"], b["key_ok"]), ("Test öncesi temiz", 2, True))
        # yedekten sonra yapılan "yanlış" işlemler
        sales.confirm(sales.create_order(self.web, [(self.serum, 5)]))
        catalog.add_image(self.soap, jpg())
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 95)
        acc = IntegrationAccount.objects.create(provider="smtp_email", name="M")
        IntegrationJob.objects.create(account=acc, kind="notify.email", idempotency_key="x", payload={})
        # yanlış onay → geri dönmez
        self.client.post("/ayarlar/yedekler/", {"action": "restore", "file": b["file"], "confirm": "evet"})
        self.assertEqual(SalesOrder.objects.count(), 1)
        r = self.client.post("/ayarlar/yedekler/", {"action": "restore", "file": b["file"], "confirm": "geri dön"})
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 100)
        self.assertFalse(self.soap.images.exists())
        self.assertTrue(self.serum.images.get().image.storage.exists(self.serum.images.get().image.name))
        self.assertEqual(len(list(Path(TMP, "media").rglob("*.jpg"))), 2)
        self.assertEqual(IntegrationAccount.objects.count(), 0)
        names = [x["name"] for x in bk.list_backups()]
        self.assertIn("Geri dönüş öncesi otomatik", names)  # dönüş öncesi hal saklandı
        # kullanıcılar ve izinler geri geldi → giriş çalışır
        self.assertTrue(self.client.login(username="boss", password="x" * 12))
        d = self.client.get(f"/ayarlar/yedekler/indir/{b['file']}")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(self.client.get("/ayarlar/yedekler/indir/..%2Fsettings.py").status_code, 404)

    def test_upload_and_other_key_warning(self):
        name = bk.create_backup("Taşıma")
        data = (Path(TMP) / "bk" / name).read_bytes()
        with override_settings(SECRET_KEY="baska-sunucu-anahtari"):
            up = bk.save_upload(SimpleUploadedFile("tasima.zip", data))
            meta = bk.read_meta(Path(TMP) / "bk" / up)
            self.assertFalse(meta["key_ok"])
            res = bk.restore_backup(up, safety_backup=False)
            self.assertIn("DJANGO_SECRET_KEY", res["warnings"][0])
        with self.assertRaises(Exception):
            bk.save_upload(SimpleUploadedFile("x.zip", b"zip degil"))

    def test_reset_test_data_keeps_master(self):
        catalog.add_image(self.serum, jpg())
        o = sales.create_order(self.web, [(self.serum, 2)])
        sales.confirm(o)
        groups = {g["label"]: g["key"] for g in bk.reset_groups() if g["kind"] == "test"}
        r = self.client.post("/ayarlar/yedekler/", {"action": "reset", "groups": [groups["Satış siparişleri"]], "confirm": "TEMİZLE"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SalesOrder.objects.count(), 1)  # sevkiyat bağlı → hiçbir şey silinmedi
        self.client.post("/ayarlar/yedekler/", {"action": "reset", "groups": list(groups.values()), "confirm": "temizle"})
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(inventory.stock_summary(self.serum)["physical"], 0)
        self.assertTrue(self.serum.images.exists())
        self.assertEqual(self.serum.__class__.objects.count(), 3)
        o2 = sales.create_order(self.web, [(self.soap, 1)])
        self.assertTrue(o2.number.endswith("000001"))

    def test_only_superuser(self):
        self.client.force_login(self.clerk)
        self.assertNotEqual(self.client.get("/ayarlar/yedekler/").status_code, 200)


@override_settings(MEDIA_ROOT=TMP + "/media2", BACKUP_ROOT=TMP + "/bk2")
class FullResetTests(ErpFixture, TransactionTestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_everything_except_users(self):
        from django.contrib.auth.models import User

        from apps.accounting.services import record_incoming_invoice
        from apps.catalog.models import Product
        from apps.inventory.models import Warehouse
        from apps.notifications.models import NotificationRule
        from apps.partners.models import Partner
        catalog.add_image(self.serum, jpg())
        sales.confirm(sales.create_order(self.web, [(self.serum, 1)]))
        record_incoming_invoice({"uuid": "6f1d3c2a-1111-4c8e-9a8b-0d4c5e6f7a81", "number": "ABC2026000000001", "total": 10})
        Partner.objects.create(name="Tedarikçi", kind="supplier")
        keys = [g["key"] for g in bk.reset_groups()]
        self.assertTrue(any(":master:" in k for k in keys))
        self.client.post("/ayarlar/yedekler/", {"action": "reset", "groups": keys, "confirm": "TEMİZLE"})
        self.assertEqual((Product.objects.count(), Partner.objects.count(), Warehouse.objects.count()), (0, 0, 0))
        from apps.accounting.models import Invoice
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertFalse(Path(TMP, "media2", "urunler").exists())
        self.assertEqual(User.objects.count(), 2)  # kullanıcılar kalır
        self.assertTrue(NotificationRule.objects.exists())  # varsayılan bildirim kuralları geri yazıldı
        self.assertTrue(self.client.login(username="boss", password="x" * 12))
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertContains(self.client.get("/ayarlar/yedekler/"), "Her şeyi seç")
        self.assertTrue(bk.list_backups()[0]["name"].startswith("Temizlik öncesi"))


class AiContextTests(ErpFixture, TransactionTestCase):
    def test_pack_download_and_in_backup(self):
        import zipfile
        self.setup_erp()
        self.client.force_login(self.boss)
        r = self.client.get("/ayarlar/yedekler/ai-rehberi/")
        body = r.content.decode()
        self.assertIn("Yapay zekâ için proje rehberi", body)
        self.assertIn("Bölüm 1 · Kurallar", body)
        self.assertIn("Modül `inventory`", body)
        from django.conf import settings
        self.assertNotIn(settings.SECRET_KEY, body)
        with override_settings(BACKUP_ROOT=TMP + "/bk3", MEDIA_ROOT=TMP + "/m3"):
            name = bk.create_backup("rehber")
            with zipfile.ZipFile(Path(TMP) / "bk3" / name) as z:
                self.assertIn("PROJE_REHBERI_AI.md", z.namelist())
