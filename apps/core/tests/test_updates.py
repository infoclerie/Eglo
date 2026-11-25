import io
import json
import zipfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.core import updates


class UpdateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="p")
        self.client.login(username="admin", password="p")

    def _make_zip(self, version="1.0.1", files=None):
        """Test için güncelleme zip'i oluşturur."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            meta = {"version": version, "description": "Test güncellemesi"}
            z.writestr("meta.json", json.dumps(meta))
            for name, content in (files or {"apps/test.py": "# test"}).items():
                z.writestr(f"files/{name}", content)
        buf.seek(0)
        buf.name = f"update-v{version}.zip"
        return buf

    def test_page_requires_superuser(self):
        """Normal kullanıcı güncellemeler sayfasına giremez."""
        self.client.logout()
        user = User.objects.create_user("normal", password="p")
        self.client.login(username="normal", password="p")
        r = self.client.get("/ayarlar/guncellemeler/")
        self.assertEqual(r.status_code, 302)  # redirect to login

    def test_page_loads(self):
        """Süper kullanıcı güncellemeler sayfasını görebilir."""
        r = self.client.get("/ayarlar/guncellemeler/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Güncellemeler")

    @override_settings(UPDATES_ROOT="/tmp/eglo-test-updates")
    def test_upload_update(self):
        """Güncelleme zip'i yüklenebilir."""
        import shutil
        shutil.rmtree("/tmp/eglo-test-updates", ignore_errors=True)
        buf = self._make_zip("1.0.1")
        r = self.client.post("/ayarlar/guncellemeler/", {"action": "upload", "file": buf}, follow=True)
        self.assertEqual(r.status_code, 200)
        # Pending listesinde görünmeli
        pending = updates.list_pending()
        self.assertTrue(any(p["version"] == "1.0.1" for p in pending))
        shutil.rmtree("/tmp/eglo-test-updates", ignore_errors=True)

    @override_settings(UPDATES_ROOT="/tmp/eglo-test-updates")
    def test_read_update_meta(self):
        """Zip'in meta bilgileri okunabilir."""
        import shutil
        import tempfile
        shutil.rmtree("/tmp/eglo-test-updates", ignore_errors=True)
        buf = self._make_zip("2.0.0", {"apps/core/views.py": "# changed", "templates/base.html": "<html>"})
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(buf.read())
            tmp.flush()
            meta = updates.read_update_meta(tmp.name)
        self.assertEqual(meta["version"], "2.0.0")
        self.assertEqual(meta["file_count"], 2)
        self.assertIn("apps/core/views.py", meta["files"])
        import os
        os.unlink(tmp.name)
        shutil.rmtree("/tmp/eglo-test-updates", ignore_errors=True)

    def test_invalid_zip_rejected(self):
        """Geçersiz dosya reddedilir."""
        buf = io.BytesIO(b"not a zip")
        buf.name = "fake.zip"
        r = self.client.post("/ayarlar/guncellemeler/", {"action": "upload", "file": buf}, follow=True)
        self.assertContains(r, "bozuk")
