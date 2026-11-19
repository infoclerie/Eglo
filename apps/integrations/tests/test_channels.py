"""Hepsiburada, ikas ve pazaryeri hakediş çekimi testleri (HTTP sahte istemciyle)."""
from decimal import Decimal as D
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.accounting.models import MarketplaceSettlement
from apps.accounting.tests.test_accounting import COMPANY
from apps.core.models import Setting
from apps.core.testing.fixtures import ErpFixture
from apps.integrations import services
from apps.integrations.models import ExternalOrder, IntegrationAccount, IntegrationJob
from apps.integrations.providers.hepsiburada import classify_hb
from apps.integrations.providers.trendyol import classify_ty
from apps.sales.models import SalesOrder
from apps.shipping import services as shipping
from apps.shipping.models import Shipment


def resp(body, status=200):
    return mock.Mock(status_code=status, content=b"x", json=lambda: body, text=str(body))


class FakeHB:
    def __init__(self, items=(), tx=()):
        self.items, self.tx, self.calls = list(items), list(tx), []

    def request(self, method, url, auth=None, headers=None, timeout=None, params=None, json=None):
        self.calls.append({"method": method, "url": url, "auth": auth, "headers": headers, "params": params, "json": json})
        if "/transactions/" in url:
            return resp({"count": len(self.tx), "items": self.tx if params["Offset"] == 0 else []})
        if method == "GET":
            return resp({"totalCount": len(self.items), "items": self.items if params["offset"] == 0 else []})
        if url.endswith("/packages/merchantid/M-1"):
            return resp({"packageNumber": "PKG-77"})
        return resp({"id": "upload-1"})


def hb_line(i, order="HB100", sku="SRM", qty=2):
    return {"id": f"L{i}", "orderNumber": order, "merchantSKU": sku, "sku": f"HBV{i}", "quantity": qty,
            "unitPrice": {"amount": 144, "currency": "TRY"}, "vatRate": 20, "status": "Open",
            "shippingAddress": {"name": "Ali Veli", "address": "Atatürk Cd. 5", "district": "Çankaya", "city": "Ankara",
                                "phoneNumber": "5321112233", "email": "ali@x.com"},
            "invoice": {"taxNumber": "1234567890", "address": {"address": "Atatürk Cd. 5"}}}


class HepsiburadaTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        Setting.put("accounting.company", COMPANY)
        self.acc = IntegrationAccount(provider="hepsiburada", name="HB", environment="live", config={
            "merchant_id": "M-1", "user_agent": "eglo_dev", "import_orders": True, "auto_confirm": True, "push_stock": True,
            "send_status": True, "own_cargo": True, "pull_settlement": True})
        self.acc.set_secrets({"service_key": "KEY"})
        self.acc.save()

    def go(self, fake, kind, payload=None, job=None):
        job = job or services.enqueue(self.acc, kind, "t", payload or {}, key=f"t:{kind}:{IntegrationJob.objects.count()}")
        with mock.patch("apps.integrations.providers.hepsiburada.requests.Session", return_value=fake):
            services.run_job(job)
        job.refresh_from_db()
        return job

    def test_import_groups_lines_auth_and_flow(self):
        fake = FakeHB([hb_line(1), hb_line(2, sku="222", qty=1), hb_line(3, order="HB101", qty=1)])
        job = self.go(fake, "hepsiburada.import_orders")
        self.assertEqual(job.status, "success", job.last_error)
        self.assertEqual(job.result["new_orders"], 2)
        c = fake.calls[0]
        self.assertEqual(c["url"], "https://oms-external.hepsiburada.com/orders/merchantid/M-1")
        self.assertEqual((c["auth"], c["headers"]["User-Agent"], c["params"]["limit"]), (("M-1", "KEY"), "eglo_dev", 100))
        o = SalesOrder.objects.get(external_ref="HB100")
        self.assertEqual((o.channel.code, o.status, o.lines.count()), ("hepsiburada", "reserved", 2))
        self.assertEqual(o.lines.get(product=self.serum).unit_price, D("120.00"))
        self.assertEqual(self.go(fake, "hepsiburada.import_orders").result["already_imported"], 2)
        # toplama → HB paket; sevk → kargoda (kendi kargo); teslim → teslim edildi
        sh = Shipment.objects.get(order=o)
        shipping.scan(sh, "111", 2)
        pkg = self.go(fake, "", job=IntegrationJob.objects.get(kind="hepsiburada.create_package"))
        self.assertEqual(pkg.result["package"], "PKG-77")
        self.assertEqual(fake.calls[-1]["json"]["lineItemRequests"], [{"id": "L1", "quantity": 2}, {"id": "L2", "quantity": 1}])
        shipping.scan(sh, "222", 1)
        shipping.pack(sh, 1)
        shipping.ship(sh, "aras", "ARAS123")
        tr = self.go(fake, "", job=IntegrationJob.objects.get(kind="hepsiburada.in_transit"))
        self.assertEqual(tr.status, "success", tr.last_error)
        self.assertTrue(fake.calls[-1]["url"].endswith("/packagenumber/PKG-77/intransit"))
        self.assertEqual(fake.calls[-1]["json"]["trackingNumber"], "ARAS123")
        shipping.deliver(sh, "Ali")
        self.assertTrue(IntegrationJob.objects.filter(kind="hepsiburada.delivered").exists())

    def test_push_stock_and_test_env(self):
        fake = FakeHB()
        self.acc.environment = "test"
        self.acc.save()
        job = self.go(fake, "hepsiburada.push_stock")
        self.assertEqual(job.status, "success", job.last_error)
        c = fake.calls[0]
        self.assertEqual(c["url"], "https://listing-external-sit.hepsiburada.com/listings/merchantid/M-1/inventory-uploads")
        rows = {r["merchantSku"]: r for r in c["json"]}
        self.assertEqual((rows["SRM"]["availableStock"], rows["SRM"]["price"]), (100, 120.0))  # liste 100 + %20 KDV

    def test_settlement_pull(self):
        tx = [{"transactionType": "Sale", "isIncome": True, "amount": {"value": 1000}},
              {"transactionType": "Commission", "isIncome": False, "amount": {"value": -150}},
              {"transactionType": "ShipmentCostSharingExpense", "isIncome": False, "amount": {"value": -40}},
              {"transactionType": "Return", "isIncome": False, "amount": {"value": -100}}]
        job = self.go(FakeHB(tx=tx), "hepsiburada.pull_settlement", {"weeks": 1})
        self.assertEqual(job.status, "success", job.last_error)
        s = MarketplaceSettlement.objects.get(channel__code="hepsiburada")
        self.assertEqual((s.gross_sales, s.commission, s.shipping, s.returns), (D("1000"), D("150"), D("40"), D("100")))
        self.assertEqual(s.expected_net, D("710"))
        self.assertEqual(classify_hb({"transactionType": "MarketingExpense"}), "ads")


class TrendyolSettlementTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.acc = IntegrationAccount(provider="trendyol", name="TY", environment="live",
                                      config={"seller_id": "9", "api_key": "K", "pull_settlement": True})
        self.acc.set_secrets({"api_secret": "S"})
        self.acc.save()

    def test_pull(self):
        def req(method, url, **kw):
            if "settlements" in url:
                return resp({"totalPages": 1, "content": [
                    {"transactionType": "Sale", "credit": 500, "commissionAmount": 75},
                    {"transactionType": "Coupon", "debt": 20}, {"transactionType": "DeliveryFee", "debt": 30}]})
            return resp({"totalPages": 1, "content": [{"transactionType": "PaymentOrder", "debt": 375},
                                                     {"transactionType": "DeductionInvoices", "debt": 0}]})
        fake = mock.Mock(request=mock.Mock(side_effect=req))
        job = services.enqueue(self.acc, "trendyol.pull_settlement", "t", {"weeks": 1})
        with mock.patch("apps.integrations.providers.trendyol.requests.Session", return_value=fake):
            services.run_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "success", job.last_error)
        url = fake.request.call_args_list[0].args[1]
        self.assertEqual(url, "https://apigw.trendyol.com/integration/finance/che/sellers/9/settlements")
        s = MarketplaceSettlement.objects.get(channel__code="trendyol")
        self.assertEqual((s.gross_sales, s.commission, s.campaign_share, s.shipping, s.bank_received),
                         (D("500"), D("75"), D("20"), D("30"), D("375")))
        self.assertEqual(s.status, "matched")
        self.assertEqual(classify_ty({"transactionType": "Return", "debt": 50, "commissionAmount": 7}),
                         [("returns", D("50")), ("commission", D("-7"))])


class IkasTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        cache.clear()
        Setting.put("accounting.company", COMPANY)
        self.acc = IntegrationAccount(provider="ikas", name="ikas", environment="live", config={
            "client_id": "CID", "channel": "web", "import_orders": True, "auto_confirm": True, "push_stock": True,
            "push_price": True, "send_status": True})
        self.acc.set_secrets({"client_secret": "SEC"})
        self.acc.save()
        self.calls = []

    def fake(self):
        order = {"id": "o-1", "orderNumber": "1001", "status": "CREATED", "note": "Kapıya bırakın",
                 "customer": {"email": "m@x.com", "firstName": "Mert", "lastName": "Kaya", "phone": "555"},
                 "shippingAddress": {"firstName": "Mert", "lastName": "Kaya", "addressLine1": "Lale Sk. 3",
                                     "city": {"name": "İzmir"}, "district": {"name": "Bornova"}, "phone": "555"},
                 "billingAddress": None,
                 "orderLineItems": [{"id": "x", "quantity": 2, "finalUnitPrice": 120, "variant": {"sku": "SRM", "barcodeList": []}}]}

        def post(url, data=None, json=None, headers=None, timeout=None):
            self.calls.append({"url": url, "data": data, "json": json, "headers": headers})
            if url.endswith("/oauth/token"):
                return resp({"access_token": "TOK", "expires_in": 14400})
            q = json["query"]
            if "listOrder" in q:
                return resp({"data": {"listOrder": {"hasNext": False, "data": [order, {**order, "orderNumber": "1002", "status": "CANCELLED"}]}}})
            if "listStockLocation" in q:
                return resp({"data": {"listStockLocation": [{"id": "loc-1", "name": "Depo"}]}})
            if "listProduct" in q:
                return resp({"data": {"listProduct": {"hasNext": False, "data": [{"id": "p-1", "variants": [{"id": "v-1", "sku": "SRM", "barcodeList": ["111"]}]}]}}})
            return resp({"data": {"saveVariantStocks": {"errors": []}, "updateVariantPrices": {"errors": []}, "fulfillOrder": {"id": "o-1"}}})
        return mock.Mock(post=mock.Mock(side_effect=post))

    def go(self, kind, payload=None, job=None):
        job = job or services.enqueue(self.acc, kind, "t", payload or {}, key=f"t:{kind}:{IntegrationJob.objects.count()}")
        with mock.patch("apps.integrations.providers.ikas.requests.Session", return_value=self.fake()):
            services.run_job(job)
        job.refresh_from_db()
        return job

    def test_orders_stock_and_fulfill(self):
        job = self.go("ikas.import_orders")
        self.assertEqual(job.status, "success", job.last_error)
        self.assertEqual(job.result["new_orders"], 1)  # iptal edilen alınmaz
        self.assertEqual(self.calls[0]["data"]["grant_type"], "client_credentials")
        self.assertEqual(self.calls[1]["headers"]["Authorization"], "Bearer TOK")
        o = SalesOrder.objects.get(external_ref="1001")
        self.assertEqual((o.channel.code, o.status, o.customer_name), ("web", "reserved", "Mert Kaya"))
        self.assertEqual(o.lines.get().unit_price, D("100.00"))
        stock = self.go("ikas.push_stock")
        self.assertEqual(stock.result["products"], 1, stock.last_error)
        m = [c for c in self.calls if c["json"] and "saveVariantStocks" in c["json"]["query"]][0]
        self.assertEqual(m["json"]["variables"]["input"]["stockInputs"][0],
                         {"productId": "p-1", "variantId": "v-1", "stockLocationId": "loc-1", "stockCount": 98})
        sh = Shipment.objects.get(order=o)
        shipping.scan(sh, "111", 2)
        shipping.pack(sh, 1)
        shipping.ship(sh, "yurtici", "YK555")
        f = self.go("", job=IntegrationJob.objects.get(kind="ikas.fulfill"))
        self.assertEqual(f.status, "success", f.last_error)
        inp = self.calls[-1]["json"]["variables"]["input"]
        self.assertEqual((inp["orderId"], inp["trackingInfoDetail"]["trackingNumber"], inp["trackingInfoDetail"]["cargoCompany"]),
                         ("o-1", "YK555", "Yurtiçi Kargo"))
        self.assertEqual(ExternalOrder.objects.get(order=o).status, "FULFILLED")


class IkasProductImportAndPanelTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        cache.clear()
        self.acc = IntegrationAccount(provider="ikas", name="ikas Mağaza", environment="live", config={"client_id": "CID", "channel": "web"})
        self.acc.set_secrets({"client_secret": "SEC"})
        self.acc.save()
        self.client.force_login(self.boss)

    def fake(self):
        products = [
            {"id": "p1", "name": "Clerie Şampuan", "description": "Saç", "brand": {"name": "Clerie"}, "categories": [{"name": "Saç bakım"}],
             "variants": [{"id": "v1", "sku": "CLR-SMP-400", "barcodeList": ["8690000000031"], "isActive": True,
                           "prices": [{"sellPrice": 240, "discountPrice": 216, "buyPrice": 60}], "stocks": [{"stockCount": 25, "stockLocationId": "L"}]}]},
            {"id": "p2", "name": "Serum yeni ad", "brand": None, "categories": [],
             "variants": [{"id": "v2", "sku": "SRM", "barcodeList": ["111"], "isActive": True, "prices": [{"sellPrice": 132}], "stocks": [{"stockCount": 9}]}]}]

        def post(url, data=None, json=None, headers=None, timeout=None):
            if url.endswith("/oauth/token"):
                return resp({"access_token": "TOK", "expires_in": 14400})
            return resp({"data": {"listProduct": {"hasNext": False, "data": products}}})
        return mock.Mock(post=mock.Mock(side_effect=post))

    def test_import_products_from_panel(self):
        from apps.catalog.models import Product, ProductPrice
        page = self.client.get(f"/integrations/kanal/{self.acc.pk}/")
        self.assertContains(page, "Ürünleri ikas'tan aktar")
        self.assertContains(page, "Satış kanalları")  # sol menü grubu
        with mock.patch("apps.integrations.providers.ikas.requests.Session", return_value=self.fake()):
            r = self.client.post(f"/integrations/kanal/{self.acc.pk}/", {"action": "products", "update_existing": "on", "import_stock": "on",
                                                                        "location": self.r1.pk, "vat_rate": "20"}, follow=True)
        self.assertContains(r, "Ürünler aktarıldı: 1 yeni ürün, 1 güncellenen, 1 açılış stoğu girilen")
        p = Product.objects.get(sku="CLR-SMP-400")
        self.assertEqual((p.name, p.barcode, p.list_price, p.brand.name, p.category.name), ("Clerie Şampuan", "8690000000031", D("200.00"), "Clerie", "Saç bakım"))
        self.assertEqual(ProductPrice.objects.get(product=p, channel=self.web).price, D("180.00"))
        from apps.inventory import services as inventory
        self.assertEqual(inventory.stock_summary(p)["available"], 25)
        self.serum.refresh_from_db()
        self.assertEqual((self.serum.name, self.serum.list_price), ("Serum yeni ad", D("110.00")))
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 100)  # stoğu olan ürüne açılış girilmez
        self.assertEqual(self.acc.listings.count(), 2)

    def test_panel_for_other_categories_redirects(self):
        mail = IntegrationAccount.objects.create(provider="smtp_email", name="Mail")
        self.assertEqual(self.client.get(f"/integrations/kanal/{mail.pk}/").status_code, 302)
