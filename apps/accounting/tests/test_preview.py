from decimal import Decimal as D

from django.test import TestCase

from apps.accounting import services
from apps.accounting.tests.test_accounting import COMPANY, ship
from apps.accounting.ubl import buyer_address_parts, invoice_notes
from apps.core.models import Setting
from apps.core.testing.fixtures import ErpFixture
from apps.sales import services as sales


class InvoicePreviewTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        Setting.put("accounting.company", COMPANY)
        self.client.force_login(self.boss)

    def test_preview_and_notes(self):
        o = sales.create_order(self.web, [(self.serum, 2)], customer_name="Raha Mousavi",
                               billing_address="Talatpaşa cad. 1012sk\nEsenyurt / İstanbul")
        sales.confirm(o)
        ship(o)
        inv = o.invoices.get(kind="sale")
        street, district, city = buyer_address_parts(inv)
        self.assertEqual((street, district, city), ("Talatpaşa cad. 1012sk", "Esenyurt", "İstanbul"))
        notes = invoice_notes(inv)
        self.assertTrue(any(n.startswith("Yalnız #") and n.endswith("Türk Lirası#") or "Kuruş#" in n for n in notes))
        self.assertIn("İrsaliye yerine geçer.", notes)
        xml = services.build_xml(inv)
        self.assertIn("Yalnız #", xml)
        self.assertIn("<cbc:CityName>İstanbul</cbc:CityName>", xml)
        r = self.client.get(f"/accounting/invoices/{inv.pk}/onizleme/")
        self.assertContains(r, "e-Arşiv Fatura")
        self.assertContains(r, "TCKN: 11111111111")
        self.assertContains(r, "Esenyurt/ İstanbul")
        self.assertContains(r, "İRSALİYE YERİNE GEÇER")
        self.assertContains(self.client.get(f"/accounting/invoices/{inv.pk}/"), "Faturayı önizle")
