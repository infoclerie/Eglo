import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.catalog import services
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory

TMP = tempfile.mkdtemp()


def photo(name="p.jpg", size=(3000, 2000), fmt="JPEG", orientation=None):
    buf = BytesIO()
    img = Image.new("RGB", size, (200, 30, 90))
    kw = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kw["exif"] = exif
    img.save(buf, fmt, **kw)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TMP)
class ProductImageTests(ErpFixture, TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_resize_rotate_main_and_reject(self):
        a = services.add_image(self.serum, photo(orientation=6))  # telefon dikey çekim (EXIF 90°)
        self.assertTrue(a.is_main)
        w, h = Image.open(a.image.path).size
        self.assertEqual((w, h), (1067, 1600))  # döndürülmüş ve 1600 px'e küçültülmüş
        self.assertEqual(max(Image.open(a.thumb.path).size), 360)
        b = services.add_image(self.serum, photo("b.png", (500, 400), "PNG"))
        self.assertFalse(b.is_main)
        services.set_main_image(b)
        a.refresh_from_db()
        self.assertEqual((self.serum.main_image, a.is_main), (b, False))
        services.delete_image(b)
        self.assertEqual(self.serum.main_image, a)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.add_image(self.serum, SimpleUploadedFile("x.jpg", b"bu bir fotograf degil"))

    def test_receive_form_with_photos_and_pages(self):
        r = self.client.get("/inventory/receive/")
        self.assertContains(r, 'capture="environment"')
        r = self.client.post("/inventory/receive/", {
            "product": self.soap.pk, "quantity": "5", "location": self.r2.pk, "lot_no": "V2", "expiry_date": "2030-01-01",
            "move_type": "purchase_in", "reference": "IRS-9", "photos": [photo("1.jpg"), photo("2.jpg")]})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(inventory.stock_summary(self.soap)["available"], 55)
        self.assertEqual(self.soap.images.count(), 2)
        self.assertEqual(self.soap.images.first().note, "Mal kabul IRS-9")
        self.assertContains(self.client.get("/inventory/scan/?code=222"), "Fotoğraflar")
        page = self.client.get(f"/catalog/{self.soap.pk}/fotograflar/")
        self.assertContains(page, "Ana görsel")
        self.client.post(f"/catalog/{self.soap.pk}/fotograflar/", {"photos": [photo("3.jpg")], "note": "koli"})
        self.assertEqual(self.soap.images.count(), 3)
        self.assertContains(self.client.get(f"/admin/catalog/product/{self.soap.pk}/change/"), "Fotoğraf ekle / yönet (3)")
        self.assertEqual(self.client.get("/admin/catalog/product/").status_code, 200)

    def test_clerk_needs_permission(self):
        self.client.force_login(self.clerk)
        self.assertEqual(self.client.get(f"/catalog/{self.soap.pk}/fotograflar/").status_code, 403)
