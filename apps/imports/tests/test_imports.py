from datetime import date
from decimal import Decimal as D
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook, load_workbook

from apps.catalog.models import Product, ProductPrice
from apps.core.testing.fixtures import ErpFixture
from apps.imports import services
from apps.inventory import services as inventory


def xlsx(rows):
    wb = Workbook()
    for r in rows:
        wb.active.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ImportTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def up(self, kind, data, confirm=True):
        r = self.client.post(f"/imports/{kind}/", {"file": SimpleUploadedFile("a.xlsx", data)})
        if confirm and r.context["rows"] and not r.context["bad"]:
            return r, self.client.post(f"/imports/{kind}/", {"confirm": "1"})
        return r, None

    def test_template_has_headers_and_example(self):
        r = self.client.get("/imports/urun/sablon/")
        ws = load_workbook(BytesIO(r.content)).active
        self.assertEqual(ws["A1"].value, "Ürün kodu (SKU)*")
        self.assertEqual(ws["A2"].value, "CLR-SRM-30")
        hdr = [c.value for c in load_workbook(BytesIO(self.client.get("/imports/fiyat/sablon/").content)).active[1]]
        self.assertIn("Fiyat: Trendyol", hdr)

    def test_products_create_update_with_turkish_numbers(self):
        data = xlsx([["Ürün kodu (SKU)*", "Ürün adı*", "Barkod", "Marka", "Tür", "Liste fiyatı (KDV hariç)", "LOT/SKT takibi (Evet/Hayır)"],
                     ["YENI-1", "Yeni Krem", 8690000000024, "Clerie", "Standart ürün", "149,90", "Hayır"],
                     ["SRM", "", None, None, None, "1.250,50", None]])
        r, done = self.up("urun", data)
        self.assertEqual(r.context["good"], 2)
        self.assertEqual(done.status_code, 302)
        p = Product.objects.get(sku="YENI-1")
        self.assertEqual((p.barcode, p.list_price, p.track_lot, p.brand.name), ("8690000000024", D("149.90"), False, "Clerie"))
        self.serum.refresh_from_db()
        self.assertEqual((self.serum.name, self.serum.list_price), ("Serum", D("1250.50")))  # boş ad korunur

    def test_errors_block_everything(self):
        data = xlsx([["Ürün kodu (SKU)*", "Ürün adı*", "Barkod", "Tür"],
                     ["OK-1", "Doğru", None, None], ["KOT-1", "", "222", "Uçan halı"]])
        r, done = self.up("urun", data)
        self.assertEqual((r.context["bad"], done), (1, None))
        errs = " ".join(r.context["rows"][1]["errors"])
        self.assertIn("ürün adı zorunlu", errs)
        self.assertIn("başka üründe", errs)
        self.assertIn("geçersiz", errs)
        self.assertFalse(Product.objects.filter(sku="OK-1").exists())

    def test_prices_and_stock(self):
        _, done = self.up("fiyat", xlsx([["Ürün kodu (SKU) veya barkod*", "Fiyat: Trendyol", "Fiyat: Web"], ["111", "130", "99,9"]]))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(ProductPrice.objects.get(product=self.serum, channel=self.ty).price, D("130"))
        self.assertEqual(ProductPrice.objects.get(product=self.serum, channel=self.web).price, D("99.90"))
        r, _ = self.up("stok", xlsx([["Ürün kodu (SKU) veya barkod*", "Lokasyon kodu*", "Adet*", "LOT / parti no", "SKT (gg.aa.yyyy)"],
                                     ["SRM", "A-01-01-01", 10, None, None]]), confirm=False)
        self.assertIn("LOT no zorunlu", r.context["rows"][0]["errors"][0])
        _, done = self.up("stok", xlsx([["Ürün kodu (SKU) veya barkod*", "Lokasyon kodu*", "Adet*", "LOT / parti no", "SKT (gg.aa.yyyy)"],
                                        ["SRM", "A-01-01-01", 10, "XL1", "31.12.2030"]]))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 110)
        self.assertEqual(self.serum.lots.get(lot_no="XL1").expiry_date, date(2030, 12, 31))

    def test_parse_helpers(self):
        self.assertEqual(services._dec("1.234,56"), D("1234.56"))
        self.assertEqual(services._date("05.01.2027"), date(2027, 1, 5))
