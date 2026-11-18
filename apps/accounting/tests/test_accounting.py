from datetime import timedelta
from decimal import Decimal as D
from xml.etree import ElementTree as ET

from django.test import TestCase

from apps.accounting import services
from apps.accounting.models import Account, ChannelCostProfile, Invoice, MarketplaceSettlement, ProductCostExtra
from apps.accounting.ubl import NS, build_invoice, to_string
from apps.core import approvals
from apps.core.models import Setting
from apps.core.testing.fixtures import ErpFixture
from apps.partners.models import Partner
from apps.purchase import services as purchase
from apps.purchase.models import SupplierQuote
from apps.sales import services as sales
from apps.shipping import services as shipping
from apps.shipping.models import Shipment

COMPANY = {"vkn": "1234567890", "title": "Eglo Kozmetik A.Ş.", "tax_office": "Kozyatağı", "street": "Koca Sinan Cd. 45C",
           "district": "Ataşehir", "city": "İstanbul", "email": "info@eglokozmetik.com"}


def ship(order):
    sh = Shipment.objects.get(order=order)
    for l in sh.lines.all():
        shipping.scan(sh, l.product.barcode, l.quantity)
    shipping.pack(sh, 1)
    shipping.ship(sh, "yurtici", "YK1")
    order.refresh_from_db()
    return order


class SalesInvoiceTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        Setting.put("accounting.company", COMPANY)
        self.bank = Account.objects.create(name="Banka", kind="bank")

    def test_earsiv_invoice_on_ship(self):
        o, _ = sales.import_channel_order("trendyol", "TY-1", [{"code": "111", "quantity": 2}], customer_name="Ayşe Yılmaz")
        ship(o)
        inv = Invoice.objects.get(sales_order=o)
        year = inv.issue_date.year
        self.assertEqual((inv.doc_type, inv.profile, inv.status), ("earsiv", "EARSIVFATURA", "ready"))
        self.assertEqual(inv.number, f"EGA{year}000000001")
        self.assertEqual((inv.subtotal, inv.vat_total, inv.total), (D("240.00"), D("48.00"), o.grand_total))

    def test_efatura_customer_ledger_payment_statement(self):
        c = Partner.objects.create(name="Kozmetik Mağazası Ltd", tax_number="9876543210", e_invoice_user=True,
                                   payment_term_days=30, group="cosmetic_store")
        o = sales.confirm(sales.create_order(self.web, [(self.serum, 10)], customer=c, payment_method="term"))
        ship(o)
        inv = Invoice.objects.get(sales_order=o)
        self.assertEqual((inv.doc_type, inv.profile), ("efatura", "TICARIFATURA"))
        self.assertEqual(inv.due_date, inv.issue_date + timedelta(days=30))
        self.assertEqual(services.balance(c), D("1200.00"))
        services.register_payment(c, self.bank, 500, invoice=inv)
        self.assertEqual(services.balance(c), D("700.00"))
        st = services.statement(c)
        self.assertEqual([r["balance"] for r in st["rows"]], [D("1200.00"), D("700.00")])
        self.assertEqual(services.overdue_receivables(inv.issue_date + timedelta(days=31))[0]["open"], D("700.00"))
        from apps.partners.services import open_balance
        self.assertEqual(open_balance(c), D("700.00"))  # kredi limiti kontrolüne bağlı

    def test_cancel_reverses_ledger(self):
        c = Partner.objects.create(name="Bayi", tax_number="1111111111")
        o = sales.confirm(sales.create_order(self.web, [(self.serum, 1)], customer=c))
        inv = Invoice.objects.get(sales_order=ship(o))
        approvals.approve(services.request_cancel(inv, self.clerk, "hatalı"), self.boss)
        inv.refresh_from_db()
        self.assertEqual((inv.status, services.balance(c)), ("cancelled", 0))

    def test_ubl_xml(self):
        o, _ = sales.import_channel_order("web", "W-1", [{"code": "111", "quantity": 2}], customer_name="Ali Veli Can",
                                          tax_number="12345678901")
        inv = Invoice.objects.get(sales_order=ship(o))
        xml = to_string(build_invoice(inv, COMPANY))
        root = ET.fromstring(xml)
        cbc, cac = "{%s}" % NS["cbc"], "{%s}" % NS["cac"]
        self.assertEqual(root.find(cbc + "ProfileID").text, "EARSIVFATURA")
        self.assertEqual(root.find(cbc + "ID").text, inv.number)
        self.assertEqual(root.find(f"{cac}LegalMonetaryTotal/{cbc}PayableAmount").text, f"{inv.total:.2f}")
        cust = root.find(f"{cac}AccountingCustomerParty/{cac}Party")
        self.assertEqual(cust.find(f"{cac}PartyIdentification/{cbc}ID").attrib["schemeID"], "TCKN")
        self.assertEqual(cust.find(f"{cac}Person/{cbc}FamilyName").text, "Can")
        self.assertEqual(root.find(f"{cac}TaxTotal/{cbc}TaxAmount").text, f"{inv.vat_total:.2f}")
        self.assertEqual(len(root.findall(cac + "InvoiceLine")), 1)


class PurchaseInvoiceTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.sup = Partner.objects.create(name="Ambalaj A.Ş.", kind="supplier", tax_number="5555555555")
        q = SupplierQuote.objects.create(supplier=self.sup, product=self.serum, unit_price=50)
        self.po = purchase.order_from_quote(q, 100, self.wh)
        approvals.approve(purchase.submit(self.po, self.clerk), self.boss)
        self.line = self.po.lines.get()
        purchase.receive_line(self.line, 80, self.r1, lot_no="P1", expiry_date=self.today + timedelta(days=500))
        self.line.refresh_from_db()

    def test_three_way_match_ok(self):
        inv = services.create_purchase_invoice(self.po, "ABC2026000000010", [(self.line, 80, "50")])
        self.assertEqual(inv.status, "posted")
        self.assertEqual(services.balance(self.sup), D("-4800.00"))  # 4000 + %20 KDV, biz borçluyuz

    def test_mismatch_needs_approval(self):
        inv = services.create_purchase_invoice(self.po, "ABC2026000000011", [(self.line, 100, "55")])
        self.assertEqual(inv.status, "on_hold")
        self.assertIn("depoya giren 80", inv.message)
        self.assertIn("sipariş fiyatı", inv.message)
        self.assertEqual(services.balance(self.sup), 0)
        from apps.core.models import ApprovalRequest
        approvals.approve(ApprovalRequest.objects.get(action="accounting.invoice_mismatch"), self.boss)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "posted")

    def test_duplicate_number_rejected(self):
        services.create_purchase_invoice(self.po, "X1", [(self.line, 10, "50")])
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.create_purchase_invoice(self.po, "X1", [(self.line, 10, "50")])


class ProfitAndSettlementTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()

    def test_document_profit_example(self):
        """Doküman §9.8: 250 − 100 − 10 − 30 − 20 − 15 − 5 = 70"""
        self.assertEqual(services.contribution(D(250), D(100), D(15), D(30), D(20), 0, D(15), 0), D(70))
        self.serum.cost = D("100")
        self.serum.save()
        ProductCostExtra.objects.create(product=self.serum, packaging_cost=10, other_cost=5)
        ChannelCostProfile.objects.create(channel=self.web, commission_pct=12, shipping_cost_per_order=20, ad_cost_pct=6)
        o = sales.confirm(sales.create_order(self.web, [(self.serum, 1, "250")]))
        ship(o)
        row = services.product_profitability(self.today - timedelta(days=1), self.today)[0]
        self.assertEqual((row["revenue"], row["product_cost"], row["commission"], row["shipping"], row["ads"]),
                         (D("250.00"), D("100.00"), D("30.00"), D("20.00"), D("15.00")))
        self.assertEqual(row["contribution"], D("70.00"))
        self.assertEqual(row["margin_pct"], D("28.00"))

    def test_settlement_reconcile(self):
        """Doküman §9.6: 100.000 − 15.000 − 3.000 − 2.000 = 80.000"""
        s = MarketplaceSettlement.objects.create(channel=self.ty, period_start=self.today, period_end=self.today,
                                                 gross_sales=100000, commission=15000, shipping=3000, service_fees=2000,
                                                 bank_received=80000)
        self.assertEqual(services.reconcile(s).status, "matched")
        s.bank_received = 79000
        services.reconcile(s)
        self.assertEqual((s.status, s.difference), ("mismatch", D("-1000")))
