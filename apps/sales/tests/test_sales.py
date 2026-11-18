from datetime import timedelta
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.core import approvals
from apps.core.events import subscribe
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory
from apps.partners.models import Partner
from apps.sales import services
from apps.sales.models import Campaign, SalesOrder


def campaign(**kw):
    now = timezone.now()
    return Campaign.objects.create(starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1), **kw)


class PricingTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()

    def test_channel_and_customer_price(self):
        self.assertEqual(services.unit_price(self.serum, self.ty), D("120.00"))
        self.assertEqual(services.unit_price(self.serum, self.web), D("100.00"))
        dealer = Partner.objects.create(name="Bayi A", group="dealer", default_channel=self.dealer_ch, discount_pct=10)
        self.assertEqual(services.unit_price(self.serum, self.web, dealer), D("54.00"))  # 60 × 0.9

    def test_totals_vat(self):
        o = services.create_order(self.web, [(self.serum, 2)], shipping_fee=D("50"))
        # 200 net + 40 KDV; kargo 50 + 10 KDV → 300
        self.assertEqual((o.subtotal, o.vat_total, o.grand_total), (D("200.00"), D("50.00"), D("300.00")))

    def test_buy_3_pay_2(self):
        campaign(name="3 al 2 öde", kind="buy_x_pay_y", x=3, y=2)
        o = services.create_order(self.web, [(self.serum, 7)])
        self.assertEqual(o.discount_total, D("200.00"))  # 7 adette 2 bedava
        self.assertEqual(o.grand_total, D("600.00"))  # 500 + %20

    def test_second_item_1tl(self):
        c = campaign(name="İkinci ürün 1 TL", kind="nth_item_price", x=2, amount=1)
        c.products.add(self.serum)
        o = services.create_order(self.web, [(self.serum, 3), (self.soap, 2)])
        self.assertEqual(o.discount_total, D("99.00"))  # yalnızca serum: 1 çift

    def test_cart_percent_with_cap_and_min(self):
        campaign(name="%10", kind="cart_percent", percent=10, min_amount=500, max_discount=30)
        small = services.create_order(self.web, [(self.serum, 2)])
        self.assertEqual(small.discount_total, 0)
        big = services.create_order(self.web, [(self.serum, 6)])
        self.assertEqual(big.discount_total, D("30.00"))
        self.assertEqual(sum(l.order_discount_share for l in big.lines.all()), D("30.00"))

    def test_coupon_and_free_shipping_and_channel_scope(self):
        c = campaign(name="Kupon", kind="coupon_percent", percent=20, coupon_code="HOSGELDIN")
        c.channels.add(self.web)
        campaign(name="Kargo bedava", kind="free_shipping_over", min_amount=150)
        o = services.create_order(self.web, [(self.serum, 2)], coupon_code="hosgeldin", shipping_fee=D("40"))
        self.assertEqual((o.discount_total, o.shipping_fee), (D("40.00"), D("0")))
        t = services.create_order(self.ty, [(self.serum, 2)], coupon_code="HOSGELDIN")
        self.assertEqual(t.discount_total, 0)  # kupon Trendyol'da geçersiz

    def test_campaign_max_uses(self):
        campaign(name="İlk 1", kind="cart_percent", percent=50, max_uses=1)
        services.confirm(services.create_order(self.web, [(self.serum, 1)]))
        self.assertEqual(services.create_order(self.web, [(self.serum, 1)]).discount_total, 0)


class OrderFlowTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()

    def test_confirm_reserves_and_blocks_oversell(self):
        o = services.create_order(self.web, [(self.serum, 60)])
        services.confirm(o)
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 40)
        o2 = services.create_order(self.ty, [(self.serum, 41)])
        with self.assertRaises(inventory.InsufficientStock):
            services.confirm(o2)
        o2.refresh_from_db()
        self.assertEqual(o2.status, "new")

    def test_kit_order_reserves_components(self):
        services.confirm(services.create_order(self.web, [(self.kit, 2)]))
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 94)

    def test_duplicate_channel_order_ignored(self):
        items = [{"code": "111", "quantity": 2, "unit_price": "120"}]
        o1, new1 = services.import_channel_order("trendyol", "TY-123", items, customer_name="Ayşe")
        o2, new2 = services.import_channel_order("trendyol", "TY-123", items, customer_name="Ayşe")
        self.assertTrue(new1)
        self.assertFalse(new2)
        self.assertEqual(o1.pk, o2.pk)
        self.assertEqual(SalesOrder.objects.count(), 1)
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 98)

    def test_case_barcode_import(self):
        o, _ = services.import_channel_order("web", "W-1", [{"code": "1110", "quantity": 1}])
        self.assertEqual(o.lines.get().quantity, 12)

    def test_unknown_barcode_rejected(self):
        with self.assertRaises(ValidationError):
            services.import_channel_order("web", "W-2", [{"code": "999", "quantity": 1}])

    def test_credit_limit_needs_approval(self):
        @subscribe("partners.collect_balance")
        def balance(partner, **kw):
            return D("900") if partner.name == "Riskli" else D("0")

        c = Partner.objects.create(name="Riskli", credit_limit=1000)
        o = services.create_order(self.web, [(self.serum, 2)], customer=c, payment_method="term")
        with self.assertRaises(services.CreditLimitExceeded):
            services.confirm(o)
        req = services.request_credit_override(o, self.clerk)
        approvals.approve(req, self.boss)
        o.refresh_from_db()
        services.confirm(o)
        self.assertEqual(SalesOrder.objects.get(pk=o.pk).status, "reserved")

    def test_cancel_after_reservation_needs_approval_and_releases(self):
        o = services.confirm(services.create_order(self.web, [(self.serum, 10)]))
        req = services.request_cancel(o, self.clerk, "müşteri vazgeçti")
        self.assertEqual(SalesOrder.objects.get(pk=o.pk).status, "reserved")
        approvals.approve(req, self.boss)
        self.assertEqual(SalesOrder.objects.get(pk=o.pk).status, "cancelled")
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 100)

    def test_new_order_cancel_without_approval(self):
        o = services.create_order(self.web, [(self.serum, 1)])
        services.request_cancel(o, self.clerk)
        self.assertEqual(SalesOrder.objects.get(pk=o.pk).status, "cancelled")
