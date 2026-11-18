import json

from django.contrib.auth.models import Group, User
from django.test import TestCase

from apps.chat.models import Presence
from apps.core.testing.fixtures import ErpFixture
from apps.partners.models import Partner
from apps.portal.models import PortalAccess


class ChatTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.sales = User.objects.create_user("satis", password="x" * 12)
        self.sales.groups.add(Group.objects.get_or_create(name="Satış ekibi")[0])
        self.dealer_user = User.objects.create_user("bayi", password="x" * 12)
        PortalAccess.objects.create(user=self.dealer_user, partner=Partner.objects.create(name="Bayi A"))

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_office_chat_and_presence(self):
        self.client.force_login(self.sales)
        self.client.get("/chat/api/poll/")  # çevrimiçi sinyal
        self.client.force_login(self.clerk)
        people = {p["name"]: p["online"] for p in self.client.get("/chat/api/people/").json()["people"]}
        self.assertTrue(people["satis"])
        self.assertFalse(people["boss"])  # hiç sinyal yok → kırmızı
        self.assertNotIn("bayi", people)  # bayi personel listesinde görünmez
        conv = self.post("/chat/api/start/", {"user": self.sales.pk}).json()["id"]
        self.post("/chat/api/send/", {"conv": conv, "body": "Merhaba, Trendyol siparişi hazır mı?"})
        self.client.force_login(self.sales)
        d = self.client.get("/chat/api/poll/").json()
        self.assertEqual(d["unread"], 1)
        msgs = self.client.get(f"/chat/api/poll/?conv={conv}&after=0").json()["messages"]
        self.assertEqual((msgs[0]["body"], msgs[0]["me"]), ("Merhaba, Trendyol siparişi hazır mı?", False))
        self.assertEqual(self.client.get("/chat/api/poll/").json()["unread"], 0)

    def test_dealer_support_isolated(self):
        self.client.force_login(self.dealer_user)
        self.assertTrue(self.client.get("/chat/api/people/").json()["support"])
        conv = self.post("/chat/api/start/", {"support": 1}).json()["id"]
        self.post("/chat/api/send/", {"conv": conv, "body": "Stok sorusu"})
        self.assertEqual(self.post("/chat/api/start/", {"user": self.sales.pk}).status_code, 403)
        self.client.force_login(self.sales)
        convs = self.client.get("/chat/api/poll/").json()["conversations"]
        self.assertEqual((convs[0]["kind"], convs[0]["unread"]), ("support", 1))
        other = User.objects.create_user("x", password="x" * 12)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/chat/api/poll/?conv={conv}").json()["messages"], [])
