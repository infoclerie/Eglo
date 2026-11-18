from datetime import timedelta
from unittest import mock
from xml.etree import ElementTree as ET

from django.test import TestCase
from django.utils import timezone

from apps.accounting.models import Invoice
from apps.accounting.tests.test_accounting import COMPANY, ship
from apps.core.models import Setting
from apps.core.testing.fixtures import ErpFixture
from apps.integrations import services
from apps.integrations.models import IntegrationAccount, IntegrationJob
from apps.integrations.providers.uyumsoft import UyumsoftClient, UyumsoftError
from apps.sales import services as sales

OK_SEND = b"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><SendInvoiceResponse xmlns="http://tempuri.org/">
<SendInvoiceResult IsSucceded="true" Message=""><Value Id="ABCDEF12-0000-0000-0000-000000000001" Number="EGA2026000000099" InvoiceScenario="eArchive"/></SendInvoiceResult>
</SendInvoiceResponse></s:Body></s:Envelope>"""
FAIL = b"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><X xmlns="http://tempuri.org/">
<XResult IsSucceded="false" Message="Kullanici adi veya sifre hatali"/></X></s:Body></s:Envelope>"""
INBOX = b"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><GetInboxInvoiceListResponse xmlns="http://tempuri.org/">
<GetInboxInvoiceListResult IsSucceded="true"><Value PageIndex="0" PageSize="100" TotalCount="1" TotalPages="1"><Items>
<InboxInvoiceListItem><InvoiceId>11111111-2222-3333-4444-555555555555</InvoiceId><DocumentId>TED2026000000123</DocumentId>
<TargetTcknVkn>5555555555</TargetTcknVkn><TargetTitle>Ambalaj A.S.</TargetTitle><ExecutionDate>2026-11-18T10:00:00</ExecutionDate>
<PayableAmount>1200.00</PayableAmount><TaxTotal>200.00</TaxTotal><TaxExclusiveAmount>1000.00</TaxExclusiveAmount>
<DocumentCurrencyCode>TRY</DocumentCurrencyCode><Status>Approved</Status></InboxInvoiceListItem></Items></Value></GetInboxInvoiceListResult>
</GetInboxInvoiceListResponse></s:Body></s:Envelope>"""


class FakeHttp:
    def __init__(self, *responses):
        self.responses, self.sent = list(responses), []

    def post(self, url, data, timeout, headers):
        self.sent.append((url, data, headers))
        body = self.responses.pop(0)
        return mock.Mock(content=body, status_code=200, text=body.decode())


class ClientTests(TestCase):
    def test_envelope_and_parse(self):
        http = FakeHttp(OK_SEND)
        c = UyumsoftClient("Uyumsoft", "Uyumsoft", "test", session=http)
        ubl = ET.fromstring('<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
                            'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"><cbc:ID>X</cbc:ID></Invoice>')
        res = c.send_invoice(ubl, "11111111111", "Ayşe", "eArchive")
        self.assertEqual(res, {"id": "ABCDEF12-0000-0000-0000-000000000001", "number": "EGA2026000000099"})
        url, data, headers = http.sent[0]
        self.assertEqual(url, "https://efatura-test.uyumsoft.com.tr/Services/Integration")
        self.assertEqual(headers["SOAPAction"], '"http://tempuri.org/IIntegration/SendInvoice"')
        xml = data.decode()
        for part in ("UsernameToken", ">Uyumsoft<", "TargetCustomer", 'VknTckn="11111111111"', ">eArchive<",
                     'DeliveryType="Electronic"', ">X</"):
            self.assertIn(part, xml)

    def test_failure_message(self):
        c = UyumsoftClient("u", "p", "test", session=FakeHttp(FAIL))
        with self.assertRaisesMessage(UyumsoftError, "sifre hatali"):
            c.system_date()


class QueueFlowTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.acc = IntegrationAccount(provider="uyumsoft_einvoice", name="Uyumsoft (Test)", environment="test",
                                      config={**COMPANY, "username": "Uyumsoft", "auto_send": True, "fetch_inbox": True,
                                              "fetch_interval": 30, "series_efatura": "EGL", "series_earsiv": "EGA"})
        self.acc.set_secrets({"password": "Uyumsoft"})
        self.acc.save()
        self.acc.provider_obj.on_activate(self.acc)

    def test_secret_encrypted(self):
        raw = IntegrationAccount.objects.filter(pk=self.acc.pk).values_list("secret", flat=True)[0]
        self.assertNotIn("Uyumsoft", raw)
        self.assertEqual(IntegrationAccount.objects.get(pk=self.acc.pk).get_secrets(), {"password": "Uyumsoft"})
        self.assertEqual(Setting.get("accounting.company")["vkn"], COMPANY["vkn"])

    def test_auto_send_after_ship(self):
        o, _ = sales.import_channel_order("trendyol", "TY-5", [{"code": "111", "quantity": 1}], customer_name="Ayşe")
        ship(o)
        inv = Invoice.objects.get(sales_order=o)
        self.assertEqual(inv.status, "queued")
        job = IntegrationJob.objects.get(kind="einvoice.send")
        with mock.patch.object(UyumsoftClient, "send_invoice", return_value={"id": "", "number": "EGA2026000000777"}) as m:
            self.assertEqual(services.run_due(), 1)
        self.assertEqual(m.call_args.args[3], "eArchive")
        inv.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual((inv.status, inv.number, job.status), ("sent", "EGA2026000000777", "success"))
        self.assertIn("EARSIVFATURA", inv.xml)
        self.assertEqual(services.enqueue(self.acc, "einvoice.send", "", {"invoice_id": inv.pk},
                                          key=f"{self.acc.pk}:send:{inv.uuid}").pk, job.pk)  # mükerrer yok

    def test_retry_backoff_and_final_failure(self):
        o, _ = sales.import_channel_order("trendyol", "TY-6", [{"code": "111", "quantity": 1}], customer_name="Ayşe")
        ship(o)
        job = IntegrationJob.objects.get(kind="einvoice.send")
        with mock.patch.object(UyumsoftClient, "send_invoice", side_effect=UyumsoftError("servis kapalı")):
            services.run_due()
            job.refresh_from_db()
            self.assertEqual((job.status, job.attempts), ("pending", 1))
            self.assertGreater(job.next_run_at, timezone.now() + timedelta(minutes=1))
            self.assertEqual(services.run_due(), 0)  # zamanı gelmedi
            IntegrationJob.objects.filter(pk=job.pk).update(attempts=4, next_run_at=timezone.now())
            services.run_due()
        job.refresh_from_db()
        inv = Invoice.objects.get(sales_order=o)
        self.assertEqual((job.status, inv.status), ("failed", "error"))
        self.assertIn("servis kapalı", inv.message)
        services.retry(job)
        with mock.patch.object(UyumsoftClient, "send_invoice", return_value={"id": "", "number": ""}):
            services.run_due()
        inv.refresh_from_db()
        self.assertEqual(inv.status, "sent")

    def test_inbox_fetch_dedup(self):
        self.assertEqual(services.schedule_periodic(), 2)
        self.assertEqual(services.schedule_periodic(), 0)  # aynı aralıkta tekrar kuyruğa girmez
        IntegrationJob.objects.filter(kind="einvoice.refresh_status").delete()
        with mock.patch("apps.integrations.providers.uyumsoft.requests", FakeHttp(INBOX, INBOX)):
            services.run_due()
            j = services.enqueue(self.acc, "einvoice.fetch_inbox", "x", {"days": 7}, key="again")
            services.run_job(j)
        inv = Invoice.objects.get(direction="in")
        self.assertEqual((inv.number, inv.total, inv.buyer_vkn, inv.source), ("TED2026000000123", 1200, "5555555555", "integrator"))
        self.assertEqual(Invoice.objects.filter(direction="in").count(), 1)


class WizardTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        self.client.force_login(self.boss)

    def test_full_wizard(self):
        base = "/integrations/new/uyumsoft_einvoice/"
        r = self.client.get(base + "credentials/?reset=1")
        self.assertContains(r, "Uyumsoft kullanıcı adı")
        r = self.client.post(base + "credentials/", {"username": "Uyumsoft", "password": "Uyumsoft", "environment": "test"})
        self.assertRedirects(r, base + "company/", fetch_redirect_response=False)
        r = self.client.post(base + "company/", {"vkn": "12", "title": "x", "tax_office": "y", "street": "s", "district": "d", "city": "c"})
        self.assertContains(r, "VKN 10")
        self.client.post(base + "company/", {**{k: COMPANY[k] for k in ("vkn", "title", "tax_office", "street", "district", "city")}})
        with mock.patch("apps.integrations.providers.uyumsoft.UyumsoftEInvoice.test_connection", return_value=(True, "Bağlandı")):
            r = self.client.get(base + "test/")
        self.assertContains(r, "Bağlantı başarılı")
        r = self.client.post(base + "settings/", {"series_efatura": "egl", "series_earsiv": "EGL", "efatura_profile": "TICARIFATURA",
                                                  "auto_send": "on", "fetch_interval": 30})
        self.assertContains(r, "farklı olmalı")
        self.client.post(base + "settings/", {"series_efatura": "egl", "series_earsiv": "ega", "efatura_profile": "TICARIFATURA",
                                              "auto_send": "on", "fetch_inbox": "on", "fetch_interval": 30})
        r = self.client.get(base + "summary/")
        self.assertContains(r, "Test ortamı")
        r = self.client.post(base + "summary/")
        acc = IntegrationAccount.objects.get()
        self.assertRedirects(r, f"/integrations/{acc.pk}/", fetch_redirect_response=False)
        self.assertEqual((acc.environment, acc.config["series_efatura"], acc.get_secrets()["password"]), ("test", "EGL", "Uyumsoft"))
        self.assertEqual(Setting.get("accounting.series_earsiv"), "EGA")
        self.assertEqual(self.client.get(f"/integrations/{acc.pk}/").status_code, 200)
        self.assertEqual(self.client.get("/integrations/").status_code, 200)
        self.assertEqual(self.client.get("/integrations/new/").status_code, 200)
        self.assertEqual(self.client.get("/integrations/jobs/").status_code, 200)
