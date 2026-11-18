"""
Uyumsoft e-Fatura / e-Arşiv entegrasyonu (SOAP, WS-Security UsernameToken).
Uç noktalar: test https://efatura-test.uyumsoft.com.tr/Services/Integration (kullanıcı/şifre: Uyumsoft/Uyumsoft)
             canlı https://efatura.uyumsoft.com.tr/Services/Integration
Kullanılan metotlar: GetSystemDate, IsEInvoiceUser, SendInvoice, GetInboxInvoiceList, QueryOutboxInvoiceStatus.
SendInvoice → InvoiceInfo { Invoice (UBL-TR), TargetCustomer @VknTckn @Alias @Title, EArchiveInvoiceInfo @DeliveryType,
Scenario (Automated | eInvoice | eArchive) }.
"""
import datetime as dt
import uuid
from xml.etree import ElementTree as ET

import requests
from django.utils import timezone

from . import Field, Provider

ENDPOINTS = {"test": "https://efatura-test.uyumsoft.com.tr/Services/Integration",
             "live": "https://efatura.uyumsoft.com.tr/Services/Integration"}
S = "http://schemas.xmlsoap.org/soap/envelope/"
T = "http://tempuri.org/"
WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
WSU = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
PWD_TYPE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText"
ARR = "http://schemas.microsoft.com/2003/10/Serialization/Arrays"
for _p, _u in {"s": S, "t": T, "o": WSSE, "u": WSU, "a": ARR}.items():
    ET.register_namespace(_p, _u)


class UyumsoftError(Exception):
    pass


def _local(tag):
    return tag.split("}", 1)[-1]


class UyumsoftClient:
    def __init__(self, username, password, environment="test", timeout=60, session=None):
        self.url = ENDPOINTS[environment]
        self.username, self.password, self.timeout = username, password, timeout
        self.http = session or requests

    def _envelope(self, body_el):
        env = ET.Element(f"{{{S}}}Envelope")
        header = ET.SubElement(env, f"{{{S}}}Header")
        sec = ET.SubElement(header, f"{{{WSSE}}}Security", {f"{{{S}}}mustUnderstand": "1"})
        now = dt.datetime.now(dt.timezone.utc)
        ts = ET.SubElement(sec, f"{{{WSU}}}Timestamp", {f"{{{WSU}}}Id": "_0"})
        ET.SubElement(ts, f"{{{WSU}}}Created").text = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        ET.SubElement(ts, f"{{{WSU}}}Expires").text = (now + dt.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        tok = ET.SubElement(sec, f"{{{WSSE}}}UsernameToken", {f"{{{WSU}}}Id": f"uuid-{uuid.uuid4()}-1"})
        ET.SubElement(tok, f"{{{WSSE}}}Username").text = self.username
        ET.SubElement(tok, f"{{{WSSE}}}Password", {"Type": PWD_TYPE}).text = self.password
        ET.SubElement(env, f"{{{S}}}Body").append(body_el)
        return ET.tostring(env, encoding="utf-8", xml_declaration=True)

    def call(self, action, body_el):
        data = self._envelope(body_el)
        try:
            r = self.http.post(self.url, data=data, timeout=self.timeout, headers={
                "Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"http://tempuri.org/IIntegration/{action}"'})
        except requests.RequestException as exc:
            raise UyumsoftError(f"Uyumsoft'a bağlanılamadı: {exc}") from exc
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError as exc:
            raise UyumsoftError(f"Beklenmeyen yanıt (HTTP {r.status_code}): {r.text[:300]}") from exc
        fault = next((e for e in root.iter() if _local(e.tag) == "Fault"), None)
        if fault is not None:
            msg = " ".join(t.strip() for t in fault.itertext() if t.strip())
            raise UyumsoftError(f"Uyumsoft hatası: {msg[:500]}")
        result = next((e for e in root.iter() if "IsSucceded" in e.attrib), None)
        if result is not None and result.attrib.get("IsSucceded", "").lower() != "true":
            raise UyumsoftError(f"Uyumsoft: {result.attrib.get('Message') or 'işlem başarısız'}")
        return root

    # ------------------------------------------------------------ metotlar
    def system_date(self):
        root = self.call("GetSystemDate", ET.Element(f"{{{T}}}GetSystemDate"))
        val = next((e for e in root.iter() if _local(e.tag) == "Value"), None)
        return (val.text if val is not None and val.text else
                next((e.attrib.get("Value") for e in root.iter() if "Value" in e.attrib), "")) or "OK"

    def is_einvoice_user(self, vkn, alias=""):
        body = ET.Element(f"{{{T}}}IsEInvoiceUser")
        ET.SubElement(body, f"{{{T}}}vknTckn").text = vkn
        ET.SubElement(body, f"{{{T}}}alias").text = alias
        root = self.call("IsEInvoiceUser", body)
        val = next((e for e in root.iter() if _local(e.tag) == "Value"), None)
        text = (val.text if val is not None else "") or next((e.attrib.get("Value", "") for e in root.iter() if "Value" in e.attrib), "")
        return str(text).lower() == "true"

    def send_invoice(self, ubl_root, target_vkn, target_title, scenario, target_alias=""):
        """ubl_root: UBL-TR Invoice elementi. Döner: {'id': ETTN, 'number': fatura no}"""
        body = ET.Element(f"{{{T}}}SendInvoice")
        info = ET.SubElement(ET.SubElement(body, f"{{{T}}}invoices"), f"{{{T}}}InvoiceInfo")
        inv = ET.SubElement(info, f"{{{T}}}Invoice")
        for child in list(ubl_root):
            inv.append(child)
        attrs = {"VknTckn": target_vkn, "Title": target_title[:200]}
        if target_alias:
            attrs["Alias"] = target_alias
        ET.SubElement(info, f"{{{T}}}TargetCustomer", attrs)
        ET.SubElement(info, f"{{{T}}}EArchiveInvoiceInfo", {"DeliveryType": "Electronic"})
        ET.SubElement(info, f"{{{T}}}Scenario").text = scenario
        root = self.call("SendInvoice", body)
        ident = next((e for e in root.iter() if _local(e.tag) in ("InvoiceIdentity", "Value") and "Id" in e.attrib), None)
        return {"id": ident.attrib.get("Id") if ident is not None else "",
                "number": ident.attrib.get("Number") if ident is not None else ""}

    def inbox_list(self, start, end, page=0, size=100):
        body = ET.Element(f"{{{T}}}GetInboxInvoiceList")
        q = ET.SubElement(body, f"{{{T}}}query", {"PageIndex": str(page), "PageSize": str(size), "OnlyNewestInvoices": "false"})
        ET.SubElement(q, f"{{{T}}}CreateStartDate").text = start.strftime("%Y-%m-%dT00:00:00")
        ET.SubElement(q, f"{{{T}}}CreateEndDate").text = end.strftime("%Y-%m-%dT23:59:59")
        root = self.call("GetInboxInvoiceList", body)
        items_el = next((e for e in root.iter() if _local(e.tag) == "Items"), None)
        out = []
        for item in (list(items_el) if items_el is not None else []):
            out.append({_local(c.tag): (c.text or "") for c in item})
        paged = next((e for e in root.iter() if "TotalPages" in e.attrib), None)
        total_pages = int(paged.attrib.get("TotalPages", "1")) if paged is not None else 1
        return out, total_pages

    def outbox_status(self, invoice_ids):
        body = ET.Element(f"{{{T}}}QueryOutboxInvoiceStatus")
        ids = ET.SubElement(body, f"{{{T}}}invoiceIds")
        for i in invoice_ids:
            ET.SubElement(ids, f"{{{ARR}}}string").text = str(i)
        root = self.call("QueryOutboxInvoiceStatus", body)
        return [dict(e.attrib) for e in root.iter() if "InvoiceId" in e.attrib]


class UyumsoftEInvoice(Provider):
    code = "uyumsoft_einvoice"
    name = "Uyumsoft e-Fatura / e-Arşiv"
    category = "einvoice"
    description = "Satış faturalarını e-Fatura veya e-Arşiv olarak gönderir, gelen e-faturaları sisteme çeker."
    color = "#0b6bcb"
    icon = "inbox"
    fields = [
        Field("username", "Uyumsoft kullanıcı adı", help="Test ortamı için: Uyumsoft"),
        Field("password", "Uyumsoft şifresi", kind="password", secret=True, help="Test ortamı için: Uyumsoft"),
        Field("environment", "Ortam", kind="choice", default="test",
              choices=[("test", "Test ortamı (önce burada deneyin)"), ("live", "Canlı ortam")]),
        Field("vkn", "Şirket VKN", step="company", help="10 haneli vergi kimlik numarası"),
        Field("title", "Şirket unvanı", step="company"),
        Field("tax_office", "Vergi dairesi", step="company"),
        Field("street", "Adres (cadde, sokak, no)", step="company"),
        Field("district", "İlçe", step="company"),
        Field("city", "İl", step="company"),
        Field("email", "E-posta", step="company", kind="email", required=False),
        Field("phone", "Telefon", step="company", required=False),
        Field("series_efatura", "e-Fatura seri ön eki", step="settings", default="EGL", help="3 harf, ör. EGL → EGL2026000000001"),
        Field("series_earsiv", "e-Arşiv seri ön eki", step="settings", default="EGA", help="3 harf, e-Fatura serisinden farklı olmalı"),
        Field("efatura_profile", "e-Fatura senaryosu", step="settings", kind="choice", default="TICARIFATURA",
              choices=[("TICARIFATURA", "Ticari fatura (alıcı kabul/ret yapabilir)"), ("TEMELFATURA", "Temel fatura")]),
        Field("auto_send", "Sevk edilen siparişin faturasını otomatik gönder", step="settings", kind="bool", default=True, required=False),
        Field("fetch_inbox", "Gelen e-faturaları otomatik çek", step="settings", kind="bool", default=True, required=False),
        Field("fetch_interval", "Gelen fatura kontrol aralığı (dakika)", step="settings", kind="int", default=30),
    ]

    @staticmethod
    def client(account=None, config=None, secrets=None, environment=None):
        if account is not None:
            config, secrets, environment = account.config, account.get_secrets(), account.environment
        return UyumsoftClient(config.get("username", ""), secrets.get("password", ""), environment or "test")

    def test_connection(self, config, secrets, environment):
        try:
            c = self.client(config=config, secrets=secrets, environment=environment)
            date = c.system_date()
            msg = f"Uyumsoft {('test' if environment == 'test' else 'canlı')} ortamına bağlanıldı (sunucu saati: {date})."
            vkn = config.get("vkn")
            if vkn:
                try:
                    msg += " Şirket e-Fatura mükellefi: " + ("EVET" if c.is_einvoice_user(vkn) else "HAYIR — kayıt kontrol edilmeli")
                except UyumsoftError as exc:
                    msg += f" (Mükellef sorgusu yapılamadı: {exc})"
            return True, msg
        except UyumsoftError as exc:
            return False, str(exc)

    def on_activate(self, account):
        from apps.core.models import Setting
        c = account.config
        Setting.put("accounting.company", {k: c.get(k, "") for k in
                                           ("vkn", "title", "tax_office", "street", "district", "city", "email", "phone")},
                    "Şirket bilgileri (e-Fatura sihirbazından)")
        Setting.put("accounting.series_efatura", (c.get("series_efatura") or "EGL").upper()[:3])
        Setting.put("accounting.series_earsiv", (c.get("series_earsiv") or "EGA").upper()[:3])
        Setting.put("accounting.efatura_profile", c.get("efatura_profile") or "TICARIFATURA")

    # ------------------------------------------------------------ işler
    def handle(self, account, job):
        from apps.accounting import services as acc
        from apps.accounting.models import Invoice
        from apps.accounting.ubl import build_invoice, to_string
        c = self.client(account)
        if job.kind == "einvoice.send":
            inv = Invoice.objects.get(pk=job.payload["invoice_id"])
            if inv.status in ("sent", "accepted"):
                return {"skipped": "zaten gönderilmiş"}
            root = build_invoice(inv, acc.company_info())
            inv.xml = to_string(root)
            inv.save(update_fields=["xml"])
            scenario = "eInvoice" if inv.doc_type == "efatura" else "eArchive"
            res = c.send_invoice(root, inv.buyer_vkn, inv.buyer_title, scenario, inv.buyer_alias)
            acc.mark_sent(inv, number=res.get("number") or None, uuid=res.get("id") or None,
                          message=f"Uyumsoft'a iletildi ({scenario}).", raw=res)
            return res
        if job.kind == "einvoice.fetch_inbox":
            days = int(job.payload.get("days", 7))
            end = timezone.localdate()
            start = end - dt.timedelta(days=days)
            created, page, pages = 0, 0, 1
            while page < pages:
                items, pages = c.inbox_list(start, end, page)
                for it in items:
                    if not it.get("InvoiceId"):
                        continue
                    _, new = acc.record_incoming_invoice({
                        "uuid": it["InvoiceId"], "number": it.get("DocumentId", ""), "vkn": it.get("TargetTcknVkn", ""),
                        "title": it.get("TargetTitle", ""), "issue_date": (it.get("ExecutionDate") or "")[:10] or None,
                        "subtotal": it.get("TaxExclusiveAmount") or 0, "vat_total": it.get("TaxTotal") or 0,
                        "total": it.get("PayableAmount") or 0, "currency": it.get("DocumentCurrencyCode") or "TRY",
                        "status": it.get("Status", ""), "raw": it})
                    created += int(new)
                page += 1
            return {"new_invoices": created}
        if job.kind == "einvoice.refresh_status":
            invs = list(Invoice.objects.filter(direction="out", status="sent", source="system").order_by("-id")[:100])
            if not invs:
                return {"updated": 0}
            by_id = {str(i.uuid).upper(): i for i in invs}
            updated = 0
            for st in c.outbox_status(list(by_id)):
                inv = by_id.get(st.get("InvoiceId", "").upper())
                if not inv:
                    continue
                status = st.get("Status", "")
                inv.external_status = status
                if any(w in status.lower() for w in ("approved", "accepted", "kabul")):
                    inv.status = "accepted"
                elif any(w in status.lower() for w in ("declined", "rejected", "red", "error", "fail")):
                    inv.status, inv.message = "rejected", st.get("Message", "")
                inv.save(update_fields=["external_status", "status", "message", "updated_at"])
                updated += 1
            return {"updated": updated}
        raise ValueError(f"Bilinmeyen iş türü: {job.kind}")

    def on_final_failure(self, account, job, error):
        if job.kind == "einvoice.send":
            from apps.accounting import services as acc
            from apps.accounting.models import Invoice
            inv = Invoice.objects.filter(pk=job.payload.get("invoice_id")).first()
            if inv:
                acc.mark_error(inv, f"Gönderilemedi ({job.attempts} deneme): {error}")
