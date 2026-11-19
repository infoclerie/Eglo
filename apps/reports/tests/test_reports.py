from django.test import TestCase

from apps.core.testing.fixtures import ErpFixture
from apps.reports.registry import REPORTS


class ReportTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_all_reports_render_and_export(self):
        self.assertContains(self.client.get("/reports/"), "Stok yaşlandırma")
        for code in REPORTS:
            r = self.client.get(f"/reports/{code}/")
            self.assertEqual(r.status_code, 200, code)
            x = self.client.get(f"/reports/{code}/?format=xlsx")
            self.assertEqual(x["Content-Type"].split(";")[0], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", code)

    def test_aging_values(self):
        data = REPORTS["stok-yaslandirma"]["fn"]({})
        row = next(r for r in data["rows"] if r["sku"] == "SRM")
        self.assertEqual((row["0–30 gün"], row["value"]), (100, 4000))
        self.assertEqual(data["totals"]["value"], 4000 + 50 * 70)

    def test_permission(self):
        self.client.force_login(self.clerk)
        self.assertEqual(self.client.get("/reports/").status_code, 403)
