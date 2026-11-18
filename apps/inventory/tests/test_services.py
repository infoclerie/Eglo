from datetime import timedelta
from decimal import Decimal as D

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import KitComponent, Product
from apps.core import approvals
from apps.core.models import AuditLog, Setting
from apps.inventory import services
from apps.inventory.models import Location, Quant, StockMove, Warehouse


class Base(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.wh = Warehouse.objects.create(code="A", name="Ana")
        self.r1 = Location.objects.create(code="A-01-01-01", warehouse=self.wh, kind="storage")
        self.r2 = Location.objects.create(code="A-01-02-01", warehouse=self.wh, kind="storage")
        self.quar = Location.objects.create(code="A-KAR", warehouse=self.wh, kind="quarantine")
        self.dmg = Location.objects.create(code="A-HAS", warehouse=self.wh, kind="damaged")
        self.ret = Location.objects.create(code="A-IADE", warehouse=self.wh, kind="return_check")
        self.p = Product.objects.create(sku="SRM", name="Serum", cost=100, min_stock=10)

    def recv(self, qty, loc, lot, days):
        return services.receive(self.p, qty, loc, lot_no=lot, expiry_date=self.today + timedelta(days=days))


class ReceiveAndMoveTests(Base):
    def test_receive_creates_lot_quant_move(self):
        self.recv(100, self.r1, "L1", 400)
        q = Quant.objects.get(product=self.p, location=self.r1)
        self.assertEqual(q.quantity, 100)
        self.assertEqual(q.lot.lot_no, "L1")
        self.assertEqual(StockMove.objects.get().move_type, "purchase_in")

    def test_lot_required_for_tracked_product(self):
        with self.assertRaises(ValidationError):
            services.receive(self.p, 5, self.r1)

    def test_expiry_computed_from_shelf_life(self):
        self.p.shelf_life_days = 365
        self.p.save()
        prod = self.today - timedelta(days=10)
        m = services.receive(self.p, 5, self.r1, lot_no="L9", production_date=prod)
        self.assertEqual(m.lot.expiry_date, prod + timedelta(days=365))

    def test_expired_lot_cannot_enter_sellable_location(self):
        with self.assertRaises(ValidationError):
            self.recv(5, self.r1, "OLD", -1)
        self.recv(5, self.quar, "OLD", -1)  # karantinaya alınabilir

    def test_transfer_keeps_total_and_blocks_overdraw(self):
        m = self.recv(50, self.r1, "L1", 400)
        services.transfer(self.p, 20, self.r1, self.r2, lot=m.lot)
        self.assertEqual(services.stock_summary(self.p)["physical"], 50)
        with self.assertRaises(services.InsufficientStock):
            services.transfer(self.p, 31, self.r1, self.r2, lot=m.lot)

    def test_audit_log_written(self):
        self.recv(1, self.r1, "L1", 400)
        self.assertTrue(AuditLog.objects.filter(model="inventory.StockMove", action="create").exists())


class ReservationTests(Base):
    def test_fefo_order(self):
        self.recv(10, self.r2, "LATE", 500)
        self.recv(10, self.r1, "EARLY", 200)
        res = services.reserve(self.p, 15, "SIP-1")
        self.assertEqual([r.quant.lot.lot_no for r in res], ["EARLY", "LATE"])
        self.assertEqual([r.quantity for r in res], [10, 5])

    def test_no_oversell_and_atomic(self):
        self.recv(10, self.r1, "L1", 400)
        with self.assertRaises(services.InsufficientStock):
            services.reserve(self.p, 11, "SIP-1")
        self.assertEqual(Quant.objects.get().reserved_quantity, 0)
        services.reserve(self.p, 10, "SIP-2")
        with self.assertRaises(services.InsufficientStock):
            services.reserve(self.p, 1, "SIP-3")

    def test_expired_and_near_expiry_skipped(self):
        self.recv(10, self.quar, "EXP", -5)
        self.recv(10, self.r1, "NEAR", 20)  # 30 günlük onay penceresinde
        with self.assertRaises(services.InsufficientStock):
            services.reserve(self.p, 1, "SIP-1")
        services.reserve(self.p, 5, "SIP-1", allow_near_expiry=True)

    def test_threshold_setting_changeable(self):
        Setting.put("inventory.expiry_thresholds", {"approval": 10})
        self.recv(10, self.r1, "NEAR", 20)
        services.reserve(self.p, 5, "SIP-1")

    def test_release_and_ship(self):
        self.recv(10, self.r1, "L1", 400)
        services.reserve(self.p, 4, "SIP-1")
        self.assertEqual(services.release("SIP-1"), 4)
        services.reserve(self.p, 6, "SIP-2")
        services.ship_reserved("SIP-2")
        q = Quant.objects.get()
        self.assertEqual((q.quantity, q.reserved_quantity), (4, 0))
        self.assertEqual(StockMove.objects.filter(move_type="sale_out").get().quantity, 6)

    def test_kit_reserves_components(self):
        kit = Product.objects.create(sku="SET3", name="3'lü", kind="kit")
        KitComponent.objects.create(kit=kit, component=self.p, quantity=3)
        self.recv(10, self.r1, "L1", 400)
        self.assertEqual(services.stock_summary(kit)["available"], 3)
        services.reserve(kit, 2, "SIP-1")
        self.assertEqual(services.stock_summary(self.p)["available"], 4)
        with self.assertRaises(services.InsufficientStock):
            services.reserve(kit, 2, "SIP-2")


class SummaryAndFormulaTests(Base):
    def test_document_example_stock_screen(self):
        """Doküman §4.2: toplam 1.250 / satışa uygun 850 / rezerve 250 / hasarlı+karantina 100 / iade 50"""
        self.recv(1100, self.r1, "L1", 400)
        self.recv(60, self.quar, "L1", 400)
        self.recv(40, self.dmg, "L1", 400)
        self.recv(50, self.ret, "L1", 400)
        services.reserve(self.p, 250, "SIP-1")
        s = services.stock_summary(self.p)
        self.assertEqual(s["physical"], 1250)
        self.assertEqual(s["available"], 850)
        self.assertEqual(s["reserved"], 250)
        self.assertEqual(s["quarantine"] + s["damaged"], 100)
        self.assertEqual(s["return_check"], 50)

    def test_purchase_suggestion_formula(self):
        """Doküman §4.4: (20 × 15) + 100 − 250 = 150"""
        self.assertEqual(services.suggest_purchase_qty(20, 15, 100, 250), 150)
        self.assertEqual(services.suggest_purchase_qty(1, 1, 0, 500), 0)
        self.assertEqual(services.suggest_purchase_qty(20, 15, 100, 250, incoming=100), 50)

    def test_purchase_suggestion_from_sales(self):
        self.p.lead_time_days, self.p.safety_stock = 15, 100
        self.p.save()
        self.recv(2000, self.r1, "L1", 400)
        services.reserve(self.p, 1800, "S")
        services.ship_reserved("S")  # 90 günde 1800 → günlük 20
        self.assertEqual(services.purchase_suggestion(self.p)["suggested_qty"], 200)  # 300+100-200

    def test_expiry_status_thresholds(self):
        m = self.recv(1, self.r1, "L", 100)
        self.assertEqual(services.expiry_status(m.lot), "warning")  # 100 gün ≤ 120
        self.assertEqual(services.expiry_status(m.lot, self.today + timedelta(days=15)), "critical")  # 85 gün
        self.assertEqual(services.expiry_status(m.lot, self.today - timedelta(days=90)), "ok")  # 190 gün
        self.assertEqual(services.expiry_status(m.lot, self.today + timedelta(days=75)), "approval")
        self.assertEqual(services.expiry_status(m.lot, self.today + timedelta(days=101)), "expired")

    def test_low_stock(self):
        self.recv(5, self.r1, "L", 400)
        self.assertEqual(services.low_stock_products()[0][0], self.p)


class CountApprovalTests(Base):
    def setUp(self):
        super().setUp()
        self.worker = User.objects.create_user("depo", password="x" * 12)
        self.boss = User.objects.create_superuser("boss", password="x" * 12)

    def test_count_needs_approval_then_adjusts(self):
        self.recv(100, self.r1, "L1", 400)
        count = services.start_count(self.wh)
        line = count.lines.get()
        line.counted_quantity = 97
        line.save()
        req = services.submit_count(count, self.worker)
        self.assertEqual(services.stock_summary(self.p)["physical"], 100)  # onaysız değişmez
        with self.assertRaises(PermissionDenied):
            approvals.approve(req, self.worker)
        approvals.approve(req, self.boss)
        count.refresh_from_db()
        self.assertEqual(count.status, "applied")
        self.assertEqual(services.stock_summary(self.p)["physical"], 97)

    def test_rejected_count_does_not_change_stock(self):
        self.recv(100, self.r1, "L1", 400)
        count = services.start_count(self.wh)
        count.lines.update(counted_quantity=150)
        approvals.reject(services.submit_count(count, self.worker), self.boss)
        count.refresh_from_db()
        self.assertEqual(count.status, "rejected")
        self.assertEqual(services.stock_summary(self.p)["physical"], 100)
