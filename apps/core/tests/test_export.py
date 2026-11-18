from io import BytesIO

from django.test import TestCase

from apps.core.testing.fixtures import ErpFixture


class ExportTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def _sheet(self, resp):
        from openpyxl import load_workbook
        self.assertEqual(resp["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        return load_workbook(BytesIO(resp.content)).active

    def test_filtered_export(self):
        ws = self._sheet(self.client.get("/admin/catalog/product/?kind__exact=standard&_export=xlsx"))
        rows = list(ws.values)
        self.assertEqual(rows[0][0], "Ürün kodu (SKU)")
        self.assertEqual(sorted(r[0] for r in rows[1:]), ["SRM", "SVS"])  # set ürün filtrelendi
        self.assertIn("Standart ürün", rows[1])  # seçenekler okunur metin

    def test_selected_action(self):
        ws = self._sheet(self.client.post("/admin/catalog/product/", {"action": "export_xlsx", "_selected_action": [self.serum.pk]}))
        self.assertEqual([r[0] for r in list(ws.values)[1:]], ["SRM"])
