from django.contrib.auth.models import User
from django.test import TestCase

from apps.inventory.models import Location, Warehouse


class DefaultWarehouseTests(TestCase):
    def test_setup_button(self):
        u = User.objects.create_superuser("a", password="x" * 12)
        self.client.force_login(u)
        r = self.client.get("/inventory/")
        self.assertContains(r, "Varsayılan depoyu oluştur")
        self.assertContains(r, "Henüz ürün yok")
        self.client.post("/inventory/", {"setup_warehouse": "1"})
        self.assertEqual(Warehouse.objects.count(), 1)
        self.assertTrue(Location.objects.filter(code="A-01-01-01", kind="storage", is_sellable=True).exists())
        self.assertTrue(Location.objects.filter(code="A-KARANTINA", is_sellable=False).exists())
        self.assertNotContains(self.client.get("/inventory/"), "Varsayılan depoyu oluştur")
