import re

from django.test import TestCase

from apps.core.testing.fixtures import ErpFixture
from apps.crm.models import Campaign
from apps.integrations.models import IntegrationAccount, IntegrationJob
from apps.partners.models import Partner


class CampaignTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)
        mail = IntegrationAccount(provider="smtp_email", name="Mail", config={"host": "smtp.x", "username": "a@x.com"})
        mail.set_secrets({"password": "p"})
        mail.save()
        IntegrationAccount.objects.create(provider="netgsm_sms", name="SMS", config={"usercode": "1", "header": "EGLO"})
        self.ok = Partner.objects.create(name="İzinli Eczane", email="ec@x.com", phone="0532 000 11 22", city="İzmir",
                                         consent_email=True, consent_sms=True)
        self.no = Partner.objects.create(name="İzinsiz Bayi", email="b@x.com", phone="05320001133", city="İzmir")
        self.nomail = Partner.objects.create(name="Mailsiz", consent_email=True)

    def test_email_campaign_consent_and_unsubscribe(self):
        r = self.client.post("/crm/kampanyalar/yeni/", {"name": "Kasım", "channel": "email", "recipient_type": "12",
                                                        "subject": "Merhaba {musteri}", "body": "Size özel %10 · {cari_kodu}"})
        c = Campaign.objects.get()
        self.assertRedirects(r, f"/crm/kampanyalar/{c.pk}/")
        page = self.client.get(f"/crm/kampanyalar/{c.pk}/")
        self.assertEqual(page.context["counts"], {"queued": 1, "no_consent": 1, "no_contact": 1})
        self.client.post(f"/crm/kampanyalar/{c.pk}/", {"test_to": "ben@x.com"})
        self.assertEqual(IntegrationJob.objects.get(ref__endswith="deneme").payload["to"], "ben@x.com")
        c.refresh_from_db()
        self.assertEqual(c.status, "draft")
        self.client.post(f"/crm/kampanyalar/{c.pk}/", {"send": "1"})
        c.refresh_from_db()
        self.assertEqual((c.status, c.queued, c.skipped), ("sent", 1, 2))
        job = IntegrationJob.objects.get(kind="notify.email", ref__contains=self.ok.code)
        self.assertEqual((job.payload["to"], job.payload["subject"]), ("ec@x.com", "Merhaba İzinli Eczane"))
        self.assertIn(self.ok.code, job.payload["body"])
        self.client.post(f"/crm/kampanyalar/{c.pk}/", {"send": "1"})  # ikinci kez gönderilmez
        self.assertEqual(IntegrationJob.objects.filter(kind="notify.email").count(), 2)
        url = re.search(r"(/crm/abonelik/[^\s]+)", job.payload["body"]).group(1)
        self.client.logout()
        self.assertContains(self.client.get(url), "Abonelikten çık")
        self.client.post(url)
        self.ok.refresh_from_db()
        self.assertFalse(self.ok.consent_email)
        self.assertEqual(self.client.get("/crm/abonelik/bozuk/").status_code, 400)

    def test_sms_campaign_iys_filter_and_city(self):
        Partner.objects.create(name="Ankara", phone="05330000000", city="Ankara", consent_sms=True)
        c = Campaign.objects.create(name="SMS", channel="sms", body="Kampanya {musteri}", city="izmir", recipient_type="11")
        self.client.post(f"/crm/kampanyalar/{c.pk}/", {"send": "1"})
        job = IntegrationJob.objects.get(kind="notify.sms")
        self.assertEqual((job.payload["to"], job.payload["iysfilter"], job.payload["text"]), ("5320001122", "11", "Kampanya İzinli Eczane"))
