from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase

from apps.core.testing.fixtures import ErpFixture
from apps.integrations.models import IntegrationAccount, IntegrationJob
from apps.notifications.models import Notification, NotificationRule
from apps.notifications.services import ensure_default_rules, normalize_phone, render
from apps.partners.models import Partner
from apps.sales import services as sales


class NotificationTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        ensure_default_rules()
        self.ecom = User.objects.create_user("eticaret", email="e@x.com", password="x" * 12)
        self.ecom.groups.add(Group.objects.get(name="E-ticaret ekibi"))
        self.mail = IntegrationAccount(provider="smtp_email", name="E-posta", config={"host": "smtp.x", "username": "a@x.com", "from_email": "a@x.com"})
        self.mail.set_secrets({"password": "p"})
        self.mail.save()
        self.sms = IntegrationAccount.objects.create(provider="netgsm_sms", name="SMS", config={"usercode": "850", "header": "EGLO"})

    def test_render_and_phone(self):
        self.assertEqual(render("Sayın {musteri}, {yok}{firma}", {"musteri": "Ali"}), "Sayın Ali, Eglo Kozmetik")
        self.assertEqual(normalize_phone("+90 (532) 162 84 22"), "5321628422")
        self.assertEqual(normalize_phone("0212 000"), "")

    def test_staff_bell_on_new_order(self):
        sales.confirm(sales.create_order(self.web, [(self.serum, 1)]))
        n = Notification.objects.get(user=self.ecom)
        self.assertTrue(n.title.startswith("Yeni sipariş: SIP-"))
        self.client.force_login(self.ecom)
        self.assertEqual(self.client.get("/notifications/api/").json()["unread"], 1)

    def test_customer_messages_only_when_enabled_with_user_template(self):
        Partner.objects.create(name="Kapalı Kural", email="k@x.com")
        self.assertFalse(IntegrationJob.objects.filter(kind="notify.email").exists())  # müşteri bildirimleri kapalı başlar
        rule = NotificationRule.objects.get(event="partner_created")
        rule.active, rule.email, rule.sms = True, True, True
        rule.subject, rule.sms_text = "Merhaba {musteri}", "Hoş geldiniz {musteri}, kodunuz {cari_kodu}"
        rule.save()
        p = Partner.objects.create(name="Yeni Bayi", email="b@x.com", phone="0532 111 22 33")
        email = IntegrationJob.objects.get(kind="notify.email")
        sms = IntegrationJob.objects.get(kind="notify.sms")
        self.assertEqual((email.payload["to"], email.payload["subject"]), ("b@x.com", "Merhaba Yeni Bayi"))
        self.assertEqual((sms.payload["to"], sms.payload["text"]), ("5321112233", f"Hoş geldiniz Yeni Bayi, kodunuz {p.code}"))

    def test_center_toggle_and_edit(self):
        self.client.force_login(self.boss)
        self.assertEqual(self.client.get("/notifications/merkez/").status_code, 200)
        rule = NotificationRule.objects.get(event="order_shipped")
        self.client.post("/notifications/merkez/", {"rule": rule.pk, "field": "sms", "value": "1"})
        rule.refresh_from_db()
        self.assertTrue(rule.sms)
        r = self.client.post(f"/notifications/merkez/{rule.pk}/", {"active": "on", "email": "on", "sms": "on", "subject": "Kargo {siparis_no}",
                                                                  "body": "Takip {takip_no}", "sms_text": "Kargo {takip_no}", "action": "save"})
        self.assertEqual(r.status_code, 302)
        r = self.client.get(f"/notifications/merkez/{rule.pk}/")
        self.assertContains(r, "Kargo SIP-000123")  # önizleme örnek veriyle

    def test_smtp_and_netgsm_send(self):
        job = IntegrationJob.objects.create(account=self.sms, kind="notify.sms", idempotency_key="t1", payload={"to": "5321112233", "text": "x"})
        with mock.patch("apps.integrations.providers.notify.requests.get", return_value=mock.Mock(text="00 123456")) as g:
            from apps.integrations.services import run_job
            run_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "success")
        self.assertEqual(g.call_args.kwargs["params"]["gsmno"], "5321112233")
        bad = IntegrationJob.objects.create(account=self.sms, kind="notify.sms", idempotency_key="t2", payload={"to": "5", "text": "x"})
        with mock.patch("apps.integrations.providers.notify.requests.get", return_value=mock.Mock(text="30")):
            run_job(bad)
        bad.refresh_from_db()
        self.assertIn("Kullanıcı adı, şifre", bad.last_error)
        from django.core import mail
        ej = IntegrationJob.objects.create(account=self.mail, kind="notify.email", idempotency_key="t3", payload={"to": "z@x.com", "subject": "S", "body": "B"})
        with mock.patch("apps.integrations.providers.notify.get_connection", return_value=mail.get_connection("django.core.mail.backends.locmem.EmailBackend")):
            run_job(ej)
        self.assertEqual((mail.outbox[0].to, mail.outbox[0].subject), (["z@x.com"], "S"))
