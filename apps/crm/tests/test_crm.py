import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.testing.fixtures import ErpFixture
from apps.crm import services
from apps.crm.models import Activity, Opportunity
from apps.partners.models import Partner
from apps.sales import services as sales
from apps.sales.models import SalesOrder


class CrmTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()

    def test_quote_creates_followup_in_3_days(self):
        o = Opportunity.objects.create(title="Otel zinciri", prospect_name="ABC Otel", owner=self.clerk)
        services.move_stage(o, "quoted", self.clerk)
        a = Activity.objects.get(opportunity=o)
        self.assertEqual((a.kind, a.due_date, o.probability), ("task", timezone.localdate() + timedelta(days=3), 50))
        self.assertEqual(services.due_activities(self.clerk, timezone.localdate() + timedelta(days=3)).count(), 1)
        self.assertEqual(services.due_activities(self.clerk).count(), 0)

    def test_board_drag_move(self):
        self.client.force_login(self.boss)
        o = Opportunity.objects.create(title="Eczane")
        r = self.client.post("/crm/move/", json.dumps({"id": o.pk, "stage": "won"}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        o.refresh_from_db()
        self.assertEqual((o.stage, o.probability), ("won", 100))
        for url in ("/crm/", "/crm/takipler/", "/crm/segmentler/"):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_segments(self):
        prospect = Partner.objects.create(name="Aday")
        new = Partner.objects.create(name="Yeni")
        sleeping = Partner.objects.create(name="Uyuyan")
        sales.create_order(self.web, [(self.serum, 1)], customer=new)
        old = sales.create_order(self.web, [(self.serum, 1)], customer=sleeping)
        SalesOrder.objects.filter(pk=old.pk).update(order_date=timezone.now() - timedelta(days=200))
        segs = {r["partner"].name: r["segment"] for r in services.segment_rows()}
        self.assertEqual((segs["Aday"], segs["Yeni"], segs["Uyuyan"]), ("prospect", "new", "sleeping"))
