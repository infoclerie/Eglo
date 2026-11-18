from datetime import timedelta
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core import approvals
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory
from apps.partners.models import Partner
from apps.purchase import services
from apps.purchase.models import PurchaseOrder, PurchaseRequest, ReceiptDiscrepancy, SupplierQuote


class PurchaseTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.sup1 = Partner.objects.create(name="Tedarikçi A", kind="supplier")
        self.sup2 = Partner.objects.create(name="Tedarikçi B", kind="supplier")

    def approved_po(self, qty=100, price="50"):
        q = SupplierQuote.objects.create(supplier=self.sup1, product=self.serum, unit_price=D(price))
        po = services.order_from_quote(q, qty, self.wh)
        approvals.approve(services.submit(po, self.clerk), self.boss)
        po.refresh_from_db()
        return po

    def test_quote_comparison(self):
        SupplierQuote.objects.create(supplier=self.sup1, product=self.serum, unit_price=50, lead_time_days=10)
        SupplierQuote.objects.create(supplier=self.sup2, product=self.serum, unit_price=50, lead_time_days=5)
        SupplierQuote.objects.create(supplier=self.sup1, product=self.serum, unit_price=55, lead_time_days=1)
        best = services.compare_quotes(self.serum)
        self.assertEqual((best[0].supplier, best[0].lead_time_days), (self.sup2, 5))

    def test_approval_required_before_receipt(self):
        q = SupplierQuote.objects.create(supplier=self.sup1, product=self.serum, unit_price=50)
        po = services.order_from_quote(q, 10, self.wh)
        with self.assertRaises(ValidationError):
            services.receive_line(po.lines.get(), 10, self.r1, lot_no="N1", expiry_date=self.today + timedelta(days=400))
        services.submit(po, self.clerk)
        self.assertEqual(PurchaseOrder.objects.get(pk=po.pk).status, "approval")

    def test_receive_updates_stock_cost_incoming(self):
        po = self.approved_po(100, "70")
        self.assertEqual(inventory.stock_summary(self.serum)["incoming"], 100)
        services.receive_line(po.lines.get(), 60, self.r1, lot_no="N1", expiry_date=self.today + timedelta(days=500))
        po.refresh_from_db()
        self.assertEqual(po.status, "partial")
        s = inventory.stock_summary(self.serum)
        self.assertEqual((s["physical"], s["incoming"]), (160, 40))
        self.serum.refresh_from_db()
        # ağırlıklı ortalama: (100×40 + 60×70) / 160 = 51.25
        self.assertEqual(self.serum.cost, D("51.25"))

    def test_over_receipt_blocked_and_short_close_discrepancy(self):
        po = self.approved_po(100)
        line = po.lines.get()
        with self.assertRaises(ValidationError):
            services.receive_line(line, 101, self.r1, lot_no="N1", expiry_date=self.today + timedelta(days=500))
        services.receive_line(line, 90, self.r1, lot_no="N1", expiry_date=self.today + timedelta(days=500))
        services.close(PurchaseOrder.objects.get(pk=po.pk))
        d = ReceiptDiscrepancy.objects.get()
        self.assertEqual((d.kind, d.ordered, d.received), ("short", 100, 90))
        self.assertEqual(PurchaseOrder.objects.get(pk=po.pk).status, "closed")
        self.assertEqual(inventory.stock_summary(self.serum)["incoming"], 0)

    def test_suggestion_creates_request_once(self):
        self.serum.min_stock, self.serum.safety_stock, self.serum.lead_time_days = 10, 500, 10
        self.serum.save()
        created = services.create_suggested_requests([self.serum])
        self.assertEqual(created[0].quantity, 400)  # 0×10 + 500 − 100
        self.assertEqual(services.create_suggested_requests([self.serum]), [])
        self.assertEqual(PurchaseRequest.objects.count(), 1)

    def test_supplier_performance(self):
        po = self.approved_po(100)
        PurchaseOrder.objects.filter(pk=po.pk).update(expected_date=self.today - timedelta(days=1))
        perf = services.supplier_performance(self.sup1)
        self.assertEqual((perf["orders"], perf["late_open"], perf["total"]), (1, 1, D("5000.00")))
