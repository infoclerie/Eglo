from decimal import Decimal as D

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounting.tests.test_accounting import COMPANY, ship
from apps.core.models import ApprovalRequest, Setting
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory
from apps.partners.models import Partner
from apps.portal.models import PortalAccess
from apps.sales.models import SalesOrder
from apps.shipping.models import Shipment


class PortalTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        Setting.put("accounting.company", COMPANY)
        self.dealer = Partner.objects.create(name="Bayi Kozmetik", group="dealer", default_channel=self.dealer_ch,
                                             discount_pct=10, payment_term_days=30, tax_number="1112223334")
        self.other = Partner.objects.create(name="Başka Bayi", group="dealer")
        self.u = User.objects.create_user("bayi1", password="x" * 12)
        PortalAccess.objects.create(user=self.u, partner=self.dealer)
        self.client.force_login(self.u)

    def test_redirect_and_internal_pages_blocked(self):
        self.assertRedirects(self.client.get("/"), "/portal/")
        self.assertEqual(self.client.get("/inventory/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_dealer_price_and_order_flow(self):
        r = self.client.get("/portal/")
        self.assertContains(r, "54,00")  # bayi fiyatı 60 − %10
        self.client.post("/portal/", {"product": self.serum.pk, "qty": 10})
        r = self.client.get("/portal/sepet/")
        self.assertContains(r, "540,00")
        r = self.client.post("/portal/sepet/", {"action": "order"})
        o = SalesOrder.objects.get()
        self.assertRedirects(r, f"/portal/siparisler/{o.pk}/")
        self.assertEqual((o.customer, o.status, o.payment_method), (self.dealer, "reserved", "term"))
        self.assertEqual(inventory.stock_summary(self.serum)["reserved"], 10)
        self.assertTrue(Shipment.objects.filter(order=o).exists())
        ship(o)
        self.assertContains(self.client.get("/portal/faturalar/"), "EGA")  # e-fatura mükellefi değil → e-Arşiv serisi
        self.assertContains(self.client.get("/portal/ekstre/"), "648,00")  # 540 + %20

    def test_credit_limit_goes_to_approval(self):
        self.dealer.credit_limit = 100
        self.dealer.save()
        self.client.post("/portal/", {"product": self.serum.pk, "qty": 10})
        self.client.post("/portal/sepet/", {"action": "order"})
        o = SalesOrder.objects.get()
        self.assertEqual(o.status, "new")
        self.assertTrue(ApprovalRequest.objects.filter(action="sales.credit_override", status="pending").exists())

    def test_min_order_amount(self):
        Setting.put("portal.min_order_amount", 1000)
        self.client.post("/portal/", {"product": self.serum.pk, "qty": 1})
        r = self.client.post("/portal/sepet/", {"action": "order"}, follow=True)
        self.assertContains(r, "Minimum sipariş tutarı")
        self.assertFalse(SalesOrder.objects.exists())

    def test_cannot_see_other_dealer_data(self):
        from apps.sales import services as sales
        foreign = sales.create_order(self.web, [(self.serum, 1)], customer=self.other)
        self.assertEqual(self.client.get(f"/portal/siparisler/{foreign.pk}/").status_code, 404)

    def test_admin_creates_portal_user(self):
        self.client.force_login(self.boss)
        r = self.client.post("/admin/portal/portalaccess/add/", {"partner": self.other.pk, "active": "on", "username": "bayi2",
                                                                 "email": "", "password": "GucluSifre2026!"})
        self.assertEqual(r.status_code, 302)
        acc = PortalAccess.objects.get(user__username="bayi2")
        self.assertEqual((acc.partner, acc.user.is_staff), (self.other, False))


class LabelTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_label_one_per_package(self):
        from apps.sales import services as sales
        from apps.shipping import services as shipping
        o, _ = sales.import_channel_order("web", "W-1", [{"code": "111", "quantity": 1}], customer_name="Ali Veli",
                                          shipping_address="Atatürk Cd. 5, Kadıköy")
        sh = Shipment.objects.get(order=o)
        shipping.scan(sh, "111")
        shipping.pack(sh, 2)
        r = self.client.get(f"/shipping/{sh.pk}/label/")
        self.assertContains(r, "Ali Veli")
        self.assertContains(r, f'data-code="{sh.number}-2"')
        self.assertContains(r, "2/2")
        self.assertEqual(self.client.get(f"/shipping/labels/?ids={sh.pk}").status_code, 200)
