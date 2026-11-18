"""Uçtan uca akış: sipariş → rezervasyon → toplama emri → barkod → paket → sevk → teslim → iade."""
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core import approvals
from apps.core.testing.fixtures import ErpFixture
from apps.inventory import services as inventory
from apps.inventory.models import StockMove
from apps.sales import services as sales
from apps.sales.models import SalesOrder
from apps.shipping import services
from apps.shipping.models import Shipment


class FlowTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.order, _ = sales.import_channel_order(
            "trendyol", "TY-1", [{"code": "111", "quantity": 2}, {"code": "222", "quantity": 1}], customer_name="Ali")
        self.sh = Shipment.objects.get(order=self.order)

    def status(self):
        return SalesOrder.objects.get(pk=self.order.pk).status

    def test_pick_list_created_in_route_order(self):
        self.assertEqual([l.location.code for l in self.sh.lines.all()], ["A-01-01-01", "A-02-01-01"])
        self.assertEqual(self.sh.expected_weight_kg, D("3.400"))

    def test_full_flow(self):
        with self.assertRaises(ValidationError):
            services.scan(self.sh, "999")  # tanınmayan barkod
        services.scan(self.sh, "111", 2)
        self.assertEqual(self.status(), "picking")
        with self.assertRaises(ValidationError):
            services.scan(self.sh, "111")  # fazla okutma
        with self.assertRaises(ValidationError):
            services.pack(self.sh, 1)  # sabun henüz toplanmadı
        services.scan(self.sh, "222")
        self.sh.refresh_from_db()
        self.assertEqual(self.sh.status, "picked")
        with self.assertRaises(ValidationError):
            services.pack(self.sh, 1, weight_kg="2.5")  # %26 sapma
        services.pack(self.sh, 1, weight_kg="3.45")
        self.assertEqual(self.status(), "packed")
        self.assertEqual(inventory.stock_summary(self.serum)["physical"], 100)  # henüz düşmedi
        services.ship(self.sh, "yurtici", "YK123")
        self.assertEqual(self.status(), "shipped")
        self.assertEqual(inventory.stock_summary(self.serum)["physical"], 98)
        self.assertEqual(inventory.stock_summary(self.serum)["reserved"], 0)
        self.sh.refresh_from_db()
        services.deliver(self.sh, "Ali")
        self.assertEqual(self.status(), "delivered")

        # iade: 1 satılabilir serum, 1 açılmış serum → açılmış olan hasarlıya gider
        rr = services.request_return(SalesOrder.objects.get(pk=self.order.pk), [(self.serum, 2)], "changed_mind")
        self.assertEqual(self.status(), "return_requested")
        services.receive_return(rr, self.clerk)
        self.assertEqual(inventory.stock_summary(self.serum)["return_check"], 2)
        line = rr.lines.get()
        req = services.inspect_return(rr, {line.pk: "opened"}, self.clerk)
        self.assertEqual(inventory.stock_summary(self.serum)["available"], 98)  # onaysız değişmez
        approvals.approve(req, self.boss)
        s = inventory.stock_summary(self.serum)
        self.assertEqual((s["damaged"], s["available"], s["return_check"]), (2, 98, 0))
        self.assertEqual(self.status(), "returned")
        self.assertEqual(StockMove.objects.filter(move_type="customer_return").get().lot.lot_no, "S1")

    def test_sellable_return_goes_back_to_stock(self):
        services.scan(self.sh, "111", 2)
        services.scan(self.sh, "222")
        services.pack(self.sh, 1)
        services.ship(self.sh, "aras")
        rr = services.request_return(SalesOrder.objects.get(pk=self.order.pk), [(self.soap, 1)], "wrong")
        services.receive_return(rr)
        approvals.approve(services.inspect_return(rr, {rr.lines.get().pk: "sellable"}), self.boss)
        self.assertEqual(inventory.stock_summary(self.soap)["available"], 50)

    def test_cancel_cancels_shipment(self):
        approvals.approve(sales.request_cancel(self.order, self.clerk), self.boss)
        self.sh.refresh_from_db()
        self.assertEqual(self.sh.status, "cancelled")

    def test_batch_pick_list(self):
        o2, _ = sales.import_channel_order("web", "W-9", [{"code": "111", "quantity": 3}])
        rows = services.batch_pick_list(Shipment.objects.all())
        self.assertEqual(rows[0], {"location": "A-01-01-01", "sku": "SRM", "lot": "S1", "quantity": D("5")})
