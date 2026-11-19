"""
Muhasebe iş kuralları (müşteri dokümanı §9). Formüller:
- Cari bakiye = Σ borç − Σ alacak  (satış faturası → borç, tahsilat → alacak; alış faturası → alacak, ödeme → borç)
- Fatura satırı KDV = net × oran / 100 ; Ödenecek = Σ net + Σ KDV
- Alış faturası 3'lü eşleştirme: faturalanan miktar ≤ teslim alınan miktar ve |fatura fiyatı − sipariş fiyatı| / sipariş fiyatı
  ≤ tolerans (%) — `accounting.price_tolerance_pct` (varsayılan 0,5). Uymazsa fatura "onay bekliyor" olur.
- Hakediş farkı = bankaya yatan − (satış − komisyon − kargo − reklam − kampanya payı − iade − hizmet bedeli)
- Katkı kârı = KDV hariç satış − ürün maliyeti − ambalaj/depolama/diğer − komisyon − kargo − hizmet − reklam − POS komisyonu
"""
from collections import defaultdict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.approvals import request_approval
from apps.core.events import publish
from apps.core.models import Sequence, Setting

from .models import (ChannelCostProfile, Invoice, InvoiceLine, LedgerEntry, MarketplaceSettlement, Payment,
                     ProductCostExtra)

ZERO = Decimal("0")
CENT = Decimal("0.01")
UNIT_CODES = {"pcs": "C62", "case": "CS", "l": "LTR", "kg": "KGM"}


def q2(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------- cari

def balance(partner, until=None):
    qs = LedgerEntry.objects.filter(partner=partner)
    if until:
        qs = qs.filter(date__lte=until)
    a = qs.aggregate(d=Sum("debit"), c=Sum("credit"))
    return (a["d"] or ZERO) - (a["c"] or ZERO)


def statement(partner, start=None, end=None):
    """Cari ekstre: devreden bakiye + hareketler ve yürüyen bakiye."""
    qs = LedgerEntry.objects.filter(partner=partner).order_by("date", "id")
    opening = ZERO
    if start:
        opening = balance(partner, start - timedelta(days=1))
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    running, rows = opening, []
    for e in qs:
        running += e.debit - e.credit
        rows.append({"entry": e, "balance": running})
    return {"opening": opening, "rows": rows, "closing": running}


def _ledger(partner, date, doc_type, description, debit=ZERO, credit=ZERO, **kw):
    if partner is None:
        return None
    return LedgerEntry.objects.create(partner=partner, date=date, doc_type=doc_type, description=description[:255],
                                      debit=debit, credit=credit, **kw)


# ---------------------------------------------------------------- numaralandırma

def next_invoice_number(doc_type, year=None):
    """GİB biçimi: 3 harf seri + yıl + 9 hane sıra (ör. EGL2026000000001). Seri: Sistem ayarı."""
    year = year or timezone.localdate().year
    key = "accounting.series_earsiv" if doc_type == "earsiv" else "accounting.series_efatura"
    prefix = (Setting.get(key) or ("EGA" if doc_type == "earsiv" else "EGL")).upper()[:3]
    code = f"invoice.{prefix}.{year}"
    Sequence.objects.get_or_create(code=code, defaults={"prefix": f"{prefix}{year}", "padding": 9})
    return Sequence.next(code, f"{prefix}{year}")


def _totals(inv):
    agg = inv.lines.aggregate(n=Sum("net_amount"), v=Sum("vat_amount"))
    inv.subtotal, inv.vat_total = agg["n"] or ZERO, agg["v"] or ZERO
    inv.total = inv.subtotal + inv.vat_total
    inv.save(update_fields=["subtotal", "vat_total", "total", "updated_at"])
    return inv


def _add_line(inv, description, quantity, net_amount, vat_rate, product=None, unit_code="C62", po_line=None):
    qty, net, rate = Decimal(str(quantity)), q2(net_amount), Decimal(str(vat_rate))
    return InvoiceLine.objects.create(invoice=inv, product=product, description=description[:255], quantity=qty,
                                      unit_code=unit_code, unit_price=(net / qty).quantize(Decimal("0.0001")) if qty else net,
                                      vat_rate=rate, net_amount=net, vat_amount=q2(net * rate / 100), po_line=po_line)


# ---------------------------------------------------------------- satış faturası

def _doc_type_for(partner, vkn):
    if partner is not None and partner.e_invoice_user:
        return "efatura"
    return "earsiv"


@transaction.atomic
def create_sales_invoice(order, user=None):
    """Sevk edilen siparişten fatura. Cari e-fatura mükellefiyse e-Fatura, değilse e-Arşiv."""
    if order.invoices.filter(kind="sale").exclude(status="cancelled").exists():
        return order.invoices.filter(kind="sale").exclude(status="cancelled").first()
    p = order.customer
    doc = _doc_type_for(p, order.tax_number)
    profile = "EARSIVFATURA" if doc == "earsiv" else Setting.get("accounting.efatura_profile", "TICARIFATURA")
    today = timezone.localdate()
    inv = Invoice.objects.create(
        direction="out", kind="sale", doc_type=doc, profile=profile, status="draft", partner=p,
        buyer_title=(p.name if p else order.customer_name) or "Nihai Tüketici",
        buyer_vkn=(p.tax_number if p else order.tax_number) or "11111111111",
        buyer_tax_office=p.tax_office if p else "", buyer_address=order.billing_address or order.shipping_address,
        buyer_city=p.city if p else "", buyer_district=p.district if p else "", buyer_email=order.email,
        issue_date=today, due_date=today + timedelta(days=p.payment_term_days if p else 0), sales_order=order)
    for l in order.lines.select_related("product"):
        _add_line(inv, l.product.name, l.quantity, l.net, l.vat_rate, product=l.product,
                  unit_code=UNIT_CODES.get(l.product.unit, "C62"))
    if order.shipping_fee:
        _add_line(inv, "Kargo hizmet bedeli", 1, order.shipping_fee, Setting.get("sales.shipping_vat_rate", 20))
    _totals(inv)
    issue(inv, user)
    return inv


@transaction.atomic
def issue(inv, user=None):
    """Taslağı resmileştirir: numara verir, cari hareket oluşturur, gönderime hazırlar."""
    if inv.status != "draft":
        raise ValidationError("Sadece taslak fatura kesilebilir.")
    if not inv.lines.exists():
        raise ValidationError("Faturada satır yok.")
    if not inv.number:
        inv.number = next_invoice_number(inv.doc_type, inv.issue_date.year)
    inv.status = "ready"
    inv.save(update_fields=["number", "status", "updated_at"])
    if inv.kind == "sale":
        _ledger(inv.partner, inv.issue_date, "invoice", f"Satış faturası {inv.number}", debit=inv.total,
                due_date=inv.due_date, invoice=inv, user=user)
    elif inv.kind == "sale_return":
        _ledger(inv.partner, inv.issue_date, "invoice", f"İade faturası {inv.number}", credit=inv.total, invoice=inv, user=user)
    publish("accounting.invoice_ready", invoice=inv)
    return inv


@transaction.atomic
def create_return_invoice(return_request, user=None):
    """Satış iadesi için iade faturası taslağı (kontrol edilip kesilir)."""
    order = return_request.order
    original = order.invoices.filter(kind="sale").exclude(status="cancelled").first()
    p = order.customer
    inv = Invoice.objects.create(
        direction="out", kind="sale_return", doc_type=original.doc_type if original else _doc_type_for(p, ""),
        profile=original.profile if original else "TEMELFATURA", status="draft", partner=p, original=original,
        buyer_title=(original.buyer_title if original else order.customer_name), buyer_vkn=original.buyer_vkn if original else "",
        buyer_address=original.buyer_address if original else order.billing_address, sales_order=order)
    prices = {l.product_id: l for l in order.lines.all()}
    for rl in return_request.lines.select_related("product"):
        ol = prices.get(rl.product_id)
        unit_net = (ol.net / ol.quantity) if ol else rl.product.list_price
        _add_line(inv, rl.product.name, rl.quantity, unit_net * rl.quantity, ol.vat_rate if ol else rl.product.vat_rate,
                  product=rl.product)
    _totals(inv)
    return inv


def mark_sent(inv, number=None, uuid=None, message="", external_status="", raw=None):
    if number:
        inv.number = number
    if uuid:
        inv.uuid = uuid
    inv.status, inv.message, inv.external_status = "sent", message, external_status
    if raw is not None:
        inv.raw = raw
    inv.save()
    publish("accounting.invoice_sent", invoice=inv)
    return inv


def mark_error(inv, message):
    inv.status, inv.message = "error", message[:2000]
    inv.save(update_fields=["status", "message", "updated_at"])
    return inv


def request_cancel(inv, user=None, reason=""):
    if inv.status == "cancelled":
        raise ValidationError("Fatura zaten iptal.")
    return request_approval("accounting.invoice_cancel", inv, f"Fatura iptali: {inv}", user, payload={"reason": reason})


@transaction.atomic
def cancel(inv, user=None, reason=""):
    for e in inv.ledger_entries.exclude(doc_type="cancel"):
        _ledger(e.partner, timezone.localdate(), "cancel", f"İptal: {e.description}", debit=e.credit, credit=e.debit,
                invoice=inv, user=user)
    inv.status, inv.message = "cancelled", reason
    inv.save(update_fields=["status", "message", "updated_at"])
    publish("accounting.invoice_cancelled", invoice=inv)
    return inv


# ---------------------------------------------------------------- alış faturası (3'lü eşleştirme)

@transaction.atomic
def create_purchase_invoice(po, number, lines, issue_date=None, user=None):
    """lines: [(satın_alma_satırı, miktar, birim_fiyat_kdv_hariç)] → eşleşirse kaydedilir, uymazsa onaya düşer."""
    if Invoice.objects.filter(direction="in", number=number).exists():
        raise ValidationError(f"{number} numaralı alış faturası zaten kayıtlı.")
    issue_date = issue_date or timezone.localdate()
    inv = Invoice.objects.create(direction="in", kind="purchase", doc_type="efatura", profile="TICARIFATURA",
                                 number=number, partner=po.supplier, buyer_title=po.supplier.name,
                                 buyer_vkn=po.supplier.tax_number, purchase_order=po, issue_date=issue_date,
                                 due_date=issue_date + timedelta(days=po.payment_term_days), status="draft")
    tol = Decimal(str(Setting.get("accounting.price_tolerance_pct", "0.5")))
    problems = []
    for pol, qty, price in lines:
        qty, price = Decimal(str(qty)), Decimal(str(price))
        already = InvoiceLine.objects.filter(po_line=pol, invoice__direction="in").exclude(
            invoice__status="cancelled").aggregate(s=Sum("quantity"))["s"] or ZERO
        if already + qty > pol.received_quantity:
            problems.append(f"{pol.product.sku}: faturalanan {already + qty} > depoya giren {pol.received_quantity}")
        if pol.unit_price and abs(price - pol.unit_price) / pol.unit_price * 100 > tol:
            problems.append(f"{pol.product.sku}: fatura fiyatı {price} ≠ sipariş fiyatı {pol.unit_price}")
        _add_line(inv, pol.product.name, qty, qty * price, pol.vat_rate, product=pol.product, po_line=pol)
    _totals(inv)
    if problems:
        inv.status, inv.message = "on_hold", "\n".join(problems)
        inv.save(update_fields=["status", "message", "updated_at"])
        request_approval("accounting.invoice_mismatch", inv, f"Alış faturası uyuşmazlığı: {number}", user,
                         payload={"problems": problems})
        return inv
    return post_purchase_invoice(inv, user)


@transaction.atomic
def post_purchase_invoice(inv, user=None):
    inv.status = "posted"
    inv.save(update_fields=["status", "updated_at"])
    _ledger(inv.partner, inv.issue_date, "invoice", f"Alış faturası {inv.number}", credit=inv.total,
            due_date=inv.due_date, invoice=inv, user=user)
    publish("accounting.purchase_invoice_posted", invoice=inv)
    return inv


@transaction.atomic
def record_incoming_invoice(data):
    """Entegratörden gelen e-faturayı kaydeder (mükerrer ETTN atlanır). Döner: (fatura, yeni_mi)"""
    from apps.partners.models import Partner
    existing = Invoice.objects.filter(uuid=data["uuid"]).first()
    if existing:
        return existing, False
    supplier = Partner.objects.filter(tax_number=data.get("vkn") or "-").first()
    inv = Invoice.objects.create(
        direction="in", kind="purchase", doc_type="efatura", profile=data.get("profile") or "TICARIFATURA",
        number=data.get("number", ""), uuid=data["uuid"], status="draft", source="integrator", partner=supplier,
        buyer_title=data.get("title", ""), buyer_vkn=data.get("vkn", ""), issue_date=data.get("issue_date") or timezone.localdate(),
        subtotal=Decimal(str(data.get("subtotal") or 0)), vat_total=Decimal(str(data.get("vat_total") or 0)),
        total=Decimal(str(data.get("total") or 0)), currency=data.get("currency") or "TRY",
        external_status=data.get("status", ""), raw=data.get("raw", {}))
    publish("accounting.incoming_invoice", invoice=inv)
    return inv, True


# ---------------------------------------------------------------- tahsilat / ödeme

@transaction.atomic
def register_payment(partner, account, amount, direction="in", date=None, method="transfer", invoice=None,
                     reference="", fee=0, user=None):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError("Tutar sıfırdan büyük olmalı.")
    if invoice is not None and amount > invoice.open_amount:
        raise ValidationError(f"Tutar faturanın açık bakiyesini ({invoice.open_amount}) aşıyor.")
    pay = Payment.objects.create(partner=partner, account=account, amount=amount, direction=direction,
                                 date=date or timezone.localdate(), method=method, invoice=invoice, reference=reference,
                                 fee=Decimal(str(fee)))
    if direction == "in":
        _ledger(partner, pay.date, "payment", f"Tahsilat {reference}".strip(), credit=amount, payment=pay, user=user)
    else:
        _ledger(partner, pay.date, "payment", f"Ödeme {reference}".strip(), debit=amount, payment=pay, user=user)
    publish("accounting.payment_registered", payment=pay)
    return pay


def overdue_receivables(today=None):
    today = today or timezone.localdate()
    out = []
    for inv in Invoice.objects.filter(direction="out", kind="sale", due_date__lt=today, partner__isnull=False).exclude(
            status__in=["draft", "cancelled"]).select_related("partner"):
        if inv.open_amount > 0:
            out.append({"invoice": inv, "days": (today - inv.due_date).days, "open": inv.open_amount})
    return sorted(out, key=lambda r: -r["days"])


def cash_flow(weeks=8, today=None):
    """Haftalık beklenen tahsilat (açık satış faturaları) ve ödemeler (açık alış faturaları), vade tarihine göre."""
    today = today or timezone.localdate()
    buckets = defaultdict(lambda: {"in": ZERO, "out": ZERO})
    for inv in Invoice.objects.exclude(status__in=["draft", "cancelled", "on_hold"]).filter(partner__isnull=False):
        if inv.open_amount <= 0:
            continue
        due = inv.due_date or inv.issue_date
        week = max(0, min(weeks, (due - today).days // 7 + (1 if (due - today).days >= 0 else 0)))
        key = "in" if inv.direction == "out" else "out"
        buckets[week][key] += inv.open_amount
    rows = []
    for w in range(0, weeks + 1):
        b = buckets[w]
        rows.append({"week": w, "label": "Vadesi geçmiş" if w == 0 else f"{w}. hafta", "in": b["in"], "out": b["out"],
                     "net": b["in"] - b["out"]})
    return rows


# ---------------------------------------------------------------- pazaryeri hakediş

def settlement_estimate(channel, start, end):
    """Sipariş verisinden beklenen hakediş tahmini (pazaryeri raporu gelene kadar)."""
    from apps.sales.models import SalesOrder
    orders = SalesOrder.objects.filter(channel=channel, status__in=["shipped", "delivered"],
                                       order_date__date__gte=start, order_date__date__lte=end)
    prof = ChannelCostProfile.objects.filter(channel=channel).first()
    gross = sum((o.grand_total for o in orders), ZERO)
    n = orders.count()
    return {"orders": n, "gross_sales": gross,
            "commission": q2(gross * prof.commission_pct / 100) if prof else ZERO,
            "shipping": q2(prof.shipping_cost_per_order * n) if prof else ZERO,
            "service_fees": q2(prof.service_fee_per_order * n) if prof else ZERO}


SETTLEMENT_FIELDS = ("gross_sales", "commission", "shipping", "ads", "campaign_share", "returns", "service_fees", "bank_received")


def upsert_settlement(channel_code, start, end, source="", **amounts):
    """
    Pazaryerinden çekilen hakediş tutarlarını dönem kaydına yazar (aynı kanal+dönem varsa günceller).
    Entegrasyon modülü çağırır. Bankaya yatan tutar API'den gelmediyse elle girilen değer korunur.
    """
    from apps.catalog.models import SalesChannel
    channel = SalesChannel.objects.get_or_create(code=channel_code, defaults={"name": channel_code.title()})[0]
    s, _ = MarketplaceSettlement.objects.get_or_create(channel=channel, period_start=start, period_end=end)
    for f in SETTLEMENT_FIELDS:
        if f in amounts and (f != "bank_received" or amounts[f]):
            setattr(s, f, q2(Decimal(str(amounts[f]))))
    stamp = f"{source} · güncellendi {timezone.localtime():%d.%m.%Y %H:%M}" if source else ""
    s.note = "\n".join([x for x in (s.note or "").splitlines() if not x.startswith(source)] + [stamp]).strip() if source else s.note
    s.save()
    if s.bank_received:
        reconcile(s)
    return s


def reconcile(settlement, tolerance=Decimal("1.00")):
    settlement.status = "matched" if abs(settlement.difference) <= tolerance else "mismatch"
    settlement.save(update_fields=["status", "updated_at"])
    return settlement


# ---------------------------------------------------------------- kârlılık

def contribution(revenue, product_cost, extra_cost, commission, shipping, service, ads, pos):
    """Katkı kârı (KDV hariç). Doküman örneği: 250 − 100 − 10 − 30 − 20 − 15 − 5 = 70"""
    return revenue - product_cost - extra_cost - commission - shipping - service - ads - pos


def product_profitability(start, end, channel=None):
    """Ürün bazında gerçek kârlılık (sevk edilen siparişler). Maliyet: sevk anındaki stok hareketi maliyeti."""
    from apps.inventory.models import StockMove
    from apps.sales.models import SalesOrder
    orders = SalesOrder.objects.filter(status__in=["shipped", "delivered", "returned", "return_requested"],
                                       order_date__date__gte=start, order_date__date__lte=end).select_related("channel")
    if channel is not None:
        orders = orders.filter(channel=channel)
    profiles = {p.channel_id: p for p in ChannelCostProfile.objects.all()}
    extras = {e.product_id: e for e in ProductCostExtra.objects.all()}
    rows = defaultdict(lambda: defaultdict(lambda: ZERO))
    for o in orders.prefetch_related("lines__product"):
        prof = profiles.get(o.channel_id)
        lines = list(o.lines.all())
        order_net = sum((l.net for l in lines), ZERO) or Decimal(1)
        cost_by_product = defaultdict(lambda: ZERO)
        for m in StockMove.objects.filter(reference=o.number, move_type="sale_out"):
            cost_by_product[m.product_id] += m.quantity * m.unit_cost
        for l in lines:
            share = l.net / order_net
            r = rows[l.product]
            r["qty"] += l.quantity
            r["revenue"] += l.net
            pc = cost_by_product.get(l.product_id)
            if l.product.is_kit:
                pc = sum((cost_by_product.get(c.component_id, ZERO) for c in l.product.components.all()), ZERO)
            r["product_cost"] += pc if pc else l.product.cost * l.quantity
            ex = extras.get(l.product_id)
            if ex:
                r["extra_cost"] += (ex.packaging_cost + ex.storage_cost + ex.other_cost) * l.quantity
            if prof:
                r["commission"] += l.net * prof.commission_pct / 100
                r["shipping"] += prof.shipping_cost_per_order * share
                r["service"] += prof.service_fee_per_order * share
                r["ads"] += l.net * prof.ad_cost_pct / 100
                if o.payment_method == "card":
                    r["pos"] += l.net * prof.pos_commission_pct / 100
    result = []
    for product, r in rows.items():
        r = {k: q2(v) if k != "qty" else v for k, v in r.items()}
        r["contribution"] = contribution(r["revenue"], r["product_cost"], r.get("extra_cost", ZERO), r.get("commission", ZERO),
                                         r.get("shipping", ZERO), r.get("service", ZERO), r.get("ads", ZERO), r.get("pos", ZERO))
        r["margin_pct"] = q2(r["contribution"] / r["revenue"] * 100) if r["revenue"] else ZERO
        result.append({"product": product, **r})
    return sorted(result, key=lambda x: -x["contribution"])


def company_info():
    """Satıcı (şirket) bilgileri — e-fatura sihirbazında girilir, Sistem ayarı `accounting.company`."""
    return Setting.get("accounting.company", {}) or {}


def build_xml(inv):
    from .ubl import build_invoice, to_string
    company = company_info()
    if not company.get("vkn"):
        raise ValidationError("Şirket bilgileri eksik: önce e-Fatura entegrasyon sihirbazını tamamlayın.")
    return to_string(build_invoice(inv, company))


def request_send(inv, user=None):
    """Entegratöre gönderim ister (entegrasyon modülü kuyruğa alır)."""
    if inv.status not in ("ready", "error"):
        raise ValidationError("Sadece gönderime hazır veya hatalı fatura gönderilebilir.")
    results = [r for r in publish("accounting.send_requested", invoice=inv, user=user) if r]
    if not results:
        raise ValidationError("Aktif e-Fatura entegrasyonu yok. Entegrasyonlar > Yeni bağlantı sihirbazını tamamlayın.")
    inv.status = "queued"
    inv.save(update_fields=["status", "updated_at"])
    return inv
