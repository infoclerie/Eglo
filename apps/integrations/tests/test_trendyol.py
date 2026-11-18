import json
from decimal import Decimal as D
from unittest import mock

from django.test import TestCase

from apps.accounting.tests.test_accounting import COMPANY, ship
from apps.core.models import Setting
from apps.core.testing.fixtures import ErpFixture
from apps.integrations import services
from apps.integrations.models import ChannelListing, ExternalOrder, IntegrationAccount, IntegrationJob
from apps.integrations.providers.trendyol import TrendyolClient
from apps.inventory import services as inventory
from apps.sales.models import SalesOrder
from apps.shipping import services as shipping
from apps.shipping.models import Shipment


def package(pid, barcode="111", qty=2, unit="144.00"):
    return {"shipmentPackageId": pid, "orderNumber": f"TY{pid}", "customerFirstName": "Ayşe", "customerLastName": "Yılmaz",
            "customerEmail": "a@x.com", "status": "Created",
            "shipmentAddress": {"fullAddress": "Bağdat Cd. 1", "district": "Kadıköy", "city": "İstanbul", "phone": "555"},
            "invoiceAddress": {"fullName": "Ayşe Yılmaz", "fullAddress": "Bağdat Cd. 1", "district": "Kadıköy", "city": "İstanbul"},
            "lines": [{"lineId": 9000 + pid, "barcode": barcode, "quantity": qty, "lineUnitPrice": unit, "vatRate": 20,
                       "productName": "Serum"}]}


class FakeTrendyol:
    def __init__(self, packages):
        self.packages, self.calls = packages, []

    def request(self, method, url, auth=None, headers=None, timeout=None, params=None, json=None):
        self.calls.append({"method": method, "url": url, "auth": auth, "headers": headers, "params": params, "json": json})
        if method == "GET":
            body = {"totalElements": len(self.packages), "totalPages": 1, "page": 0, "content": self.packages}
        elif "price-and-inventory" in url:
            body = {"batchRequestId": "batch-1"}
        else:
            body = {}
        return mock.Mock(status_code=200, content=b"x", json=lambda: body, text=str(body))


class TrendyolTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        Setting.put("accounting.company", COMPANY)
        self.acc = IntegrationAccount(provider="trendyol", name="Trendyol", environment="live",
                                      config={"seller_id": "123456", "api_key": "KEY", "import_orders": True, "auto_confirm": True,
                                              "order_interval": 5, "push_stock": True, "stock_interval": 15, "stock_buffer": 2,
                                              "send_status": True})
        self.acc.set_secrets({"api_secret": "SECRET"})
        self.acc.save()

    def run_with(self, fake, kind, payload=None):
        job = services.enqueue(self.acc, kind, "t", payload or {}, key=f"t:{kind}:{IntegrationJob.objects.count()}")
        with mock.patch("apps.integrations.providers.trendyol.requests.Session", return_value=fake):
            services.run_job(job)
        job.refresh_from_db()
        return job

    def test_auth_headers_and_v2_endpoint(self):
        fake = FakeTrendyol([])
        TrendyolClient("123456", "K", "S", session=fake).orders(__import__("django.utils.timezone").utils.timezone.now(),
                                                                __import__("django.utils.timezone").utils.timezone.now())
        call = fake.calls[0]
        self.assertEqual(call["url"], "https://apigw.trendyol.com/integration/order/sellers/123456/v2/orders")
        self.assertEqual(call["headers"]["User-Agent"], "123456 - SelfIntegration")
        self.assertEqual(call["auth"], ("K", "S"))
        self.assertEqual(call["params"]["status"], "Created")

    def test_import_orders_dedup_and_reserve(self):
        fake = FakeTrendyol([package(1), package(2, qty=1)])
        job = self.run_with(fake, "trendyol.import_orders")
        self.assertEqual(job.status, "success", job.last_error)
        self.assertEqual(job.result["new_orders"], 2)
        o = SalesOrder.objects.get(external_ref="1")
        self.assertEqual((o.channel.code, o.status, o.customer_name), ("trendyol", "reserved", "Ayşe Yılmaz"))
        line = o.lines.get()
        self.assertEqual(line.unit_price, D("120.00"))  # 144 KDV dahil → 120 KDV hariç
        self.assertEqual(o.grand_total, D("288.00"))
        self.assertEqual(inventory.stock_summary(self.serum)["reserved"], 3)
        job2 = self.run_with(fake, "trendyol.import_orders")
        self.assertEqual((job2.result["new_orders"], job2.result["already_imported"]), (0, 2))
        self.assertEqual(SalesOrder.objects.count(), 2)

    def test_unmapped_product_fails_then_mapping_fixes(self):
        fake = FakeTrendyol([package(5, barcode="TY-BARKOD-X")])
        job = self.run_with(fake, "trendyol.import_orders")
        self.assertEqual(job.status, "pending")  # yeniden denenecek
        self.assertIn("eşleşmedi", job.last_error)
        ChannelListing.objects.create(account=self.acc, product=self.serum, external_barcode="TY-BARKOD-X")
        job = self.run_with(fake, "trendyol.import_orders")
        self.assertEqual(job.status, "success")
        self.assertTrue(SalesOrder.objects.filter(external_ref="5").exists())

    def test_insufficient_stock_keeps_order_new(self):
        job = self.run_with(FakeTrendyol([package(7, qty=500)]), "trendyol.import_orders")
        self.assertEqual(job.status, "success")
        self.assertEqual(SalesOrder.objects.get(external_ref="7").status, "new")
        self.assertTrue(job.result["not_confirmed"])

    def test_push_stock_with_buffer_and_vat(self):
        fake = FakeTrendyol([])
        job = self.run_with(fake, "trendyol.push_stock")
        self.assertEqual(job.status, "success", job.last_error)
        items = {i["barcode"]: i for i in fake.calls[0]["json"]["items"]}
        self.assertEqual(items["111"]["quantity"], 98)  # 100 − güvenlik payı 2
        self.assertEqual(items["111"]["salePrice"], 144.0)  # Trendyol kanal fiyatı 120 + %20 KDV
        self.assertEqual(items["222"]["quantity"], 48)
        self.assertNotIn(None, items)

    def test_status_updates_and_stock_change_trigger(self):
        self.run_with(FakeTrendyol([package(11)]), "trendyol.import_orders")
        self.assertTrue(IntegrationJob.objects.filter(kind="trendyol.push_stock", ref__contains="değişiklik").exists())
        o = SalesOrder.objects.get(external_ref="11")
        sh = Shipment.objects.get(order=o)
        shipping.scan(sh, "111", 2)
        picking = IntegrationJob.objects.get(kind="trendyol.update_status", ref__endswith="Picking")
        fake = FakeTrendyol([])
        with mock.patch("apps.integrations.providers.trendyol.requests.Session", return_value=fake):
            services.run_job(picking)
        put = fake.calls[0]
        self.assertEqual(put["url"], "https://apigw.trendyol.com/integration/order/sellers/123456/shipment-packages/11")
        self.assertEqual(put["json"], {"lines": [{"lineId": 9011, "quantity": 2}], "params": {}, "status": "Picking"})
        shipping.pack(sh, 1)
        shipping.ship(sh, "tex", "TEX1")
        inv_job = IntegrationJob.objects.get(kind="trendyol.update_status", ref__endswith="Invoiced")
        self.assertTrue(inv_job.payload["params"]["invoiceNumber"].startswith("EGA"))
        self.assertEqual(ExternalOrder.objects.get().order, o)

    def test_periodic_jobs(self):
        n = services.schedule_periodic()
        kinds = set(IntegrationJob.objects.values_list("kind", flat=True))
        self.assertEqual((n, kinds), (2, {"trendyol.import_orders", "trendyol.push_stock"}))

    def test_wizard_trendyol(self):
        self.client.force_login(self.boss)
        base = "/integrations/new/trendyol/"
        self.client.get(base + "credentials/?reset=1")
        r = self.client.post(base + "credentials/", {"seller_id": "123456", "api_key": "K", "api_secret": "S", "environment": "live"})
        self.assertRedirects(r, base + "test/", fetch_redirect_response=False)
        with mock.patch("apps.integrations.providers.trendyol.Trendyol.test_connection", return_value=(True, "Bağlandı")):
            self.assertContains(self.client.get(base + "test/"), "Bağlantı başarılı")
        self.client.post(base + "settings/", {"import_orders": "on", "auto_confirm": "on", "order_interval": 5, "push_stock": "on",
                                              "stock_interval": 15, "stock_buffer": 1, "send_status": "on"})
        self.client.post(base + "summary/")
        acc = IntegrationAccount.objects.filter(provider="trendyol", active=True).get()
        self.assertEqual((acc.config["seller_id"], acc.get_secrets()["api_secret"], acc.config["stock_buffer"]), ("123456", "S", 1))
        self.assertEqual(self.client.get(f"/integrations/{acc.pk}/listings/").status_code, 200)
        r = self.client.post(f"/integrations/{acc.pk}/listings/", {f"bc_{self.serum.pk}": "TY-1", f"sync_{self.serum.pk}": "on"})
        self.assertEqual(ChannelListing.objects.get(account=acc, product=self.serum).external_barcode, "TY-1")
