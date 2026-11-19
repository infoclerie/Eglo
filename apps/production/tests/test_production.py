from datetime import timedelta
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory
from apps.inventory.models import StockMove
from apps.partners.models import Partner
from apps.production import services as prod
from apps.production.models import BillOfMaterials, BomLine


class ProductionTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.base = Product.objects.create(sku="HM-BAZ", name="Serum bazı (kg)", kind="raw", unit="kg", cost=50, track_lot=True)
        self.bottle = Product.objects.create(sku="AMB-30", name="30 ml şişe", kind="packaging", cost=4, track_lot=False)
        self.serum.shelf_life_days = 730
        self.serum.save()
        inventory.receive(self.base, 10, self.r1, lot_no="B-OLD", expiry_date=self.today + timedelta(days=60))
        inventory.receive(self.base, 20, self.r2, lot_no="B-NEW", expiry_date=self.today + timedelta(days=400))
        inventory.receive(self.bottle, 1000, self.r1)
        self.bom = BillOfMaterials.objects.create(product=self.serum, code="RCT-SRM", batch_size=100)
        BomLine.objects.create(bom=self.bom, component=self.base, quantity=3, scrap_pct=10)   # 100 adet için 3 kg + %10 fire
        BomLine.objects.create(bom=self.bom, component=self.bottle, quantity=100)

    def test_full_flow_fefo_quarantine_qc_and_cost(self):
        req = dict((c.sku, q) for c, q in prod.requirements(self.bom, 200))
        self.assertEqual(req, {"HM-BAZ": D("6.600"), "AMB-30": D("200.000")})
        o = prod.create_order(self.bom, 200, self.wh)
        self.assertTrue(o.number.startswith("URT-"))
        before = inventory.stock_summary(self.serum)["available"]
        prod.confirm(o)
        self.assertEqual(inventory.stock_summary(self.base)["reserved"], D("6.600"))
        self.assertEqual(inventory.stock_summary(self.serum)["incoming"], 200)
        prod.start(o)
        lots = {m.lot.lot_no for m in StockMove.objects.filter(reference=o.number, product=self.base)}
        self.assertEqual(lots, {"B-OLD"})  # FEFO: SKT'si yakın parti önce (yakın SKT hammaddede kullanılabilir)
        o.refresh_from_db()
        self.assertEqual((o.status, o.material_cost), ("in_progress", D("6.6") * 50 + 200 * 4))
        prod.finish(o, 190)
        o.refresh_from_db()
        self.assertEqual((o.status, o.unit_cost, o.waste_pct), ("qc", (D("1130") / 190).quantize(D("0.0001")), D("5.00")))
        s = inventory.stock_summary(self.serum)
        self.assertEqual((s["quarantine"], s["available"]), (190, before))  # karantinada; satışa kapalı
        lot = self.serum.lots.get(lot_no=o.number)
        self.assertEqual(lot.expiry_date, self.today + timedelta(days=730))
        with self.assertRaises(ValidationError):
            prod.quality_check(o, False, "")  # red nedeni zorunlu
        prod.quality_check(o, True, "Analiz uygun")
        self.assertEqual(inventory.stock_summary(self.serum)["available"], before + 190)
        self.assertEqual(o.status, "done")

    def test_shortage_blocks_and_cancel_releases(self):
        o = prod.create_order(self.bom, 2000, self.wh)  # 66 kg baz gerekir, 30 var
        with self.assertRaises(ValidationError) as e:
            prod.confirm(o)
        self.assertIn("HM-BAZ", str(e.exception))
        self.assertEqual(inventory.stock_summary(self.base)["reserved"], 0)
        o2 = prod.create_order(self.bom, 100, self.wh)
        prod.confirm(o2)
        prod.cancel(o2)
        self.assertEqual(inventory.stock_summary(self.base)["reserved"], 0)

    def test_subcontract_cost_and_screens(self):
        fason = Partner.objects.create(name="Fason Kimya", kind="supplier")
        with self.assertRaises(ValidationError):
            prod.create_order(self.bom, 100, self.wh, kind="subcontract")
        o = prod.create_order(self.bom, 100, self.wh, kind="subcontract", subcontractor=fason, subcontract_unit_cost=D("2.5"))
        self.client.force_login(self.boss)
        self.assertContains(self.client.get(f"/production/{o.pk}/"), "Malzemeyi ayır")
        self.client.post(f"/production/{o.pk}/", {"action": "confirm"})
        self.client.post(f"/production/{o.pk}/", {"action": "start"})
        o.refresh_from_db()
        self.assertEqual(o.status, "at_subcontractor")
        self.client.post(f"/production/{o.pk}/", {"action": "finish", "produced_qty": "100"})
        o.refresh_from_db()
        self.assertEqual(o.unit_cost, ((D("3.3") * 50 + 400 + 250) / 100).quantize(D("0.0001")))
        self.assertEqual(self.client.get("/production/").status_code, 200)
        r = self.client.post("/production/yeni/", {"bom": self.bom.pk, "quantity": "50", "warehouse": self.wh.pk, "kind": "internal"})
        self.assertEqual(r.status_code, 302)
