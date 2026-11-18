import json
from unittest import mock

from django.test import TestCase

from apps.core import rates
from apps.core.models import UserPreference
from apps.core.testing.fixtures import ErpFixture
from apps.sales import services as sales

TRUNCGIL = ('{"Update_Date":"2026-11-19","USD":{"Buying":50.45,"Type":"Currency","Selling":50.47,"Change":0.06},'
            '"EUR":{"Buying":55.33,"Type":"Currency","Selling":55.67,"Change":-0.19},'
            '"GRA":{"Selling":6044.63,"Type":"Gold","Name":"GRAMALTIN","Change":0.07,"Buying":6043.81},"XX":{"Bu')  # yarım yanıt


class DashboardTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_rates_parse_truncated_response(self):
        with mock.patch("apps.core.rates.requests.get", return_value=mock.Mock(text=TRUNCGIL)):
            r = rates.fetch()
        self.assertEqual([x["code"] for x in r], ["USD", "EUR", "GRA"])
        self.assertEqual((r[2]["sell"], r[1]["change"]), (6044.63, -0.19))

    def test_dashboard_charts_and_toggle(self):
        sales.confirm(sales.create_order(self.web, [(self.serum, 2)]))
        with mock.patch("apps.core.rates.fetch", return_value=[]):
            self.assertEqual(self.client.get("/api/kurlar/").json(), {"rates": []})
        r = self.client.get("/")
        self.assertContains(r, "Son 30 gün ciro")
        self.assertContains(r, "Kanallara göre satış")
        self.client.post("/ayarlar/panel-duzeni/", json.dumps({"hidden": ["sales.chart-kanal"]}), content_type="application/json")
        r = self.client.get("/")
        self.assertNotContains(r, 'data-key="sales.chart-kanal" href')
        self.assertEqual(UserPreference.objects.get(user=self.boss).hidden_widgets, ["sales.chart-kanal"])
        self.assertContains(r, 'class="card chart-card wide" data-key="sales.chart-ciro-30"')
