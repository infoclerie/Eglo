"""
UBL-TR 1.2 fatura XML üretici (GİB e-Fatura / e-Arşiv). Entegratörden bağımsızdır.
Satıcı bilgileri `company` sözlüğünden gelir: vkn, title, tax_office, street, district, city, email, phone.
Mali imzayı özel entegratör (Uyumsoft) atar; burada sadece cac:Signature referansı bulunur.
"""
from decimal import Decimal
from xml.etree import ElementTree as ET

from django.utils import timezone

NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}
for _p, _u in NS.items():
    ET.register_namespace(_p, _u)

CAC, CBC, INV = "{%s}" % NS["cac"], "{%s}" % NS["cbc"], "{%s}" % NS[""]


def _m(v):
    return f"{Decimal(v):.2f}"


def _sub(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, tag, {k.replace("_", ""): str(v) for k, v in attrs.items()})
    if text is not None:
        el.text = str(text)
    return el


def _party(parent, wrapper, vkn, title, tax_office, street, district, city, email="", phone=""):
    party = _sub(_sub(parent, CAC + wrapper), CAC + "Party")
    scheme = "TCKN" if len(vkn or "") == 11 else "VKN"
    _sub(_sub(party, CAC + "PartyIdentification"), CBC + "ID", vkn, schemeID=scheme)
    if scheme == "VKN":
        _sub(_sub(party, CAC + "PartyName"), CBC + "Name", title)
    addr = _sub(party, CAC + "PostalAddress")
    _sub(addr, CBC + "StreetName", street or "-")
    _sub(addr, CBC + "CitySubdivisionName", district or "-")
    _sub(addr, CBC + "CityName", city or "-")
    _sub(_sub(addr, CAC + "Country"), CBC + "Name", "Türkiye")
    _sub(_sub(_sub(party, CAC + "PartyTaxScheme"), CAC + "TaxScheme"), CBC + "Name", tax_office or "-")
    if email or phone:
        c = _sub(party, CAC + "Contact")
        if phone:
            _sub(c, CBC + "Telephone", phone)
        if email:
            _sub(c, CBC + "ElectronicMail", email)
    if scheme == "TCKN":
        parts = (title or "Nihai Tüketici").split()
        person = _sub(party, CAC + "Person")
        _sub(person, CBC + "FirstName", " ".join(parts[:-1]) or parts[0])
        _sub(person, CBC + "FamilyName", parts[-1] if len(parts) > 1 else "-")
    return party


def _tax_total(parent, groups, currency):
    tt = _sub(parent, CAC + "TaxTotal")
    _sub(tt, CBC + "TaxAmount", _m(sum((g[1] for g in groups.values()), Decimal(0))), currencyID=currency)
    for rate, (base, tax) in sorted(groups.items()):
        st = _sub(tt, CAC + "TaxSubtotal")
        _sub(st, CBC + "TaxableAmount", _m(base), currencyID=currency)
        _sub(st, CBC + "TaxAmount", _m(tax), currencyID=currency)
        _sub(st, CBC + "Percent", f"{Decimal(rate):g}")
        scheme = _sub(_sub(st, CAC + "TaxCategory"), CAC + "TaxScheme")
        _sub(scheme, CBC + "Name", "KDV")
        _sub(scheme, CBC + "TaxTypeCode", "0015")
    return tt


def build_invoice(inv, company):
    """Fatura modelinden UBL-TR Invoice elementi (ElementTree) üretir."""
    cur = inv.currency
    root = ET.Element(INV + "Invoice")
    _sub(root, CBC + "UBLVersionID", "2.1")
    _sub(root, CBC + "CustomizationID", "TR1.2")
    _sub(root, CBC + "ProfileID", inv.profile)
    _sub(root, CBC + "ID", inv.number)
    _sub(root, CBC + "CopyIndicator", "false")
    _sub(root, CBC + "UUID", str(inv.uuid).upper())
    _sub(root, CBC + "IssueDate", inv.issue_date.isoformat())
    _sub(root, CBC + "IssueTime", timezone.localtime().strftime("%H:%M:%S"))
    _sub(root, CBC + "InvoiceTypeCode", "IADE" if inv.kind.endswith("return") else "SATIS")
    if inv.sales_order_id:
        _sub(root, CBC + "Note", f"Sipariş no: {inv.sales_order.number}"
             + (f" / {inv.sales_order.external_ref}" if inv.sales_order.external_ref else ""))
    _sub(root, CBC + "DocumentCurrencyCode", cur)
    _sub(root, CBC + "LineCountNumeric", inv.lines.count())
    if inv.sales_order_id:
        od = _sub(root, CAC + "OrderReference")
        _sub(od, CBC + "ID", inv.sales_order.external_ref or inv.sales_order.number)
        _sub(od, CBC + "IssueDate", inv.sales_order.order_date.date().isoformat())
    if inv.original_id:
        ref = _sub(_sub(root, CAC + "BillingReference"), CAC + "InvoiceDocumentReference")
        _sub(ref, CBC + "ID", inv.original.number)
        _sub(ref, CBC + "IssueDate", inv.original.issue_date.isoformat())
    sig = _sub(root, CAC + "Signature")
    _sub(sig, CBC + "ID", company["vkn"], schemeID="VKN_TCKN")
    sp = _sub(sig, CAC + "SignatoryParty")
    _sub(_sub(sp, CAC + "PartyIdentification"), CBC + "ID", company["vkn"], schemeID="VKN")
    a = _sub(sp, CAC + "PostalAddress")
    _sub(a, CBC + "CitySubdivisionName", company.get("district") or "-")
    _sub(a, CBC + "CityName", company.get("city") or "-")
    _sub(_sub(a, CAC + "Country"), CBC + "Name", "Türkiye")
    _sub(_sub(_sub(sig, CAC + "DigitalSignatureAttachment"), CAC + "ExternalReference"), CBC + "URI", "#Signature")

    _party(root, "AccountingSupplierParty", company["vkn"], company["title"], company.get("tax_office"),
           company.get("street"), company.get("district"), company.get("city"), company.get("email"), company.get("phone"))
    _party(root, "AccountingCustomerParty", inv.buyer_vkn, inv.buyer_title, inv.buyer_tax_office, inv.buyer_address,
           inv.buyer_district, inv.buyer_city, inv.buyer_email)

    lines = list(inv.lines.all())
    groups = {}
    for l in lines:
        base, tax = groups.get(l.vat_rate, (Decimal(0), Decimal(0)))
        groups[l.vat_rate] = (base + l.net_amount, tax + l.vat_amount)
    _tax_total(root, groups, cur)

    lmt = _sub(root, CAC + "LegalMonetaryTotal")
    _sub(lmt, CBC + "LineExtensionAmount", _m(inv.subtotal), currencyID=cur)
    _sub(lmt, CBC + "TaxExclusiveAmount", _m(inv.subtotal), currencyID=cur)
    _sub(lmt, CBC + "TaxInclusiveAmount", _m(inv.total), currencyID=cur)
    _sub(lmt, CBC + "AllowanceTotalAmount", "0.00", currencyID=cur)
    _sub(lmt, CBC + "PayableAmount", _m(inv.total), currencyID=cur)

    for i, l in enumerate(lines, 1):
        il = _sub(root, CAC + "InvoiceLine")
        _sub(il, CBC + "ID", i)
        _sub(il, CBC + "InvoicedQuantity", f"{l.quantity.normalize():f}", unitCode=l.unit_code)
        _sub(il, CBC + "LineExtensionAmount", _m(l.net_amount), currencyID=cur)
        _tax_total(il, {l.vat_rate: (l.net_amount, l.vat_amount)}, cur)
        item = _sub(il, CAC + "Item")
        _sub(item, CBC + "Name", l.description)
        if l.product_id:
            _sub(_sub(item, CAC + "SellersItemIdentification"), CBC + "ID", l.product.sku)
        _sub(_sub(il, CAC + "Price"), CBC + "PriceAmount", f"{l.unit_price:.4f}", currencyID=cur)
    return root


def to_string(element):
    return ET.tostring(element, encoding="unicode")
