"""
Asistanın kullanabileceği veri sorguları (salt okunur). Yapay zekâ veritabanına doğrudan erişmez; yalnız bu fonksiyonları çağırır.
Her araç: ad, açıklama (yapay zekâya), giriş şeması, gereken izin(ler), fonksiyon(user, **girdi) → JSON uyumlu sözlük.
KVKK: Müşteri telefon, e-posta, adres, VKN/TCKN hiçbir araç çıktısında yer almaz.
Yeni araç: TOOLS listesine ekleyin; izin kontrolü ve satır sınırı otomatik uygulanır.
"""
import datetime as dt
from decimal import Decimal

from django.apps import apps
from django.db.models import Q, Sum
from django.utils import timezone

MAX_ROWS = 40


def _d(v):
    if isinstance(v, Decimal):
        return float(v.quantize(Decimal("0.01")))
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    return v


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj][:MAX_ROWS]
    return _d(obj)


def _period(args):
    today = timezone.localdate()
    def parse(k, default):
        try:
            return dt.date.fromisoformat(str(args.get(k)))
        except (TypeError, ValueError):
            return default
    start = parse("start", today.replace(day=1))
    end = parse("end", today)
    return (start, end) if start <= end else (end, start)


PERIOD = {"start": {"type": "string", "description": "Başlangıç tarihi YYYY-AA-GG (varsayılan: bu ayın 1'i)"},
          "end": {"type": "string", "description": "Bitiş tarihi YYYY-AA-GG (varsayılan: bugün)"}}


def _channel(code):
    from apps.catalog.models import SalesChannel
    if not code:
        return None
    return SalesChannel.objects.filter(Q(code__iexact=code) | Q(name__icontains=code)).first()


VALID = ["payment_ok", "reserved", "picking", "picked", "packed", "invoiced", "shipped", "delivered", "return_requested", "returned"]


# ---------------------------------------------------------------- satış
def sales_summary(user, **a):
    from apps.sales.models import SalesOrder
    start, end = _period(a)
    qs = SalesOrder.objects.filter(order_date__date__gte=start, order_date__date__lte=end)
    ch = _channel(a.get("channel"))
    if ch:
        qs = qs.filter(channel=ch)
    valid = qs.exclude(status__in=["cancelled", "new", "awaiting_payment"])
    by = {}
    for o in valid.select_related("channel"):
        r = by.setdefault(o.channel.name, {"orders": 0, "revenue_excl_vat": Decimal(0), "total_incl_vat": Decimal(0)})
        r["orders"] += 1
        r["revenue_excl_vat"] += o.grand_total - o.vat_total
        r["total_incl_vat"] += o.grand_total
    return {"period": [start, end], "channel_filter": ch.name if ch else "tümü",
            "orders": valid.count(), "cancelled": qs.filter(status="cancelled").count(),
            "waiting_new": qs.filter(status__in=["new", "awaiting_payment"]).count(),
            "revenue_excl_vat": sum((r["revenue_excl_vat"] for r in by.values()), Decimal(0)),
            "total_incl_vat": sum((r["total_incl_vat"] for r in by.values()), Decimal(0)),
            "by_channel": [{"channel": k, **v} for k, v in sorted(by.items(), key=lambda x: -x[1]["revenue_excl_vat"])]}


def top_products(user, **a):
    from apps.sales.models import SalesOrderLine
    start, end = _period(a)
    qs = SalesOrderLine.objects.filter(order__order_date__date__gte=start, order__order_date__date__lte=end,
                                       order__status__in=VALID).select_related("product")
    ch = _channel(a.get("channel"))
    if ch:
        qs = qs.filter(order__channel=ch)
    rows = {}
    for l in qs:
        r = rows.setdefault(l.product.sku, {"sku": l.product.sku, "name": l.product.name, "qty": Decimal(0), "revenue_excl_vat": Decimal(0)})
        r["qty"] += l.quantity
        r["revenue_excl_vat"] += l.net
    key = "qty" if a.get("sort") == "qty" else "revenue_excl_vat"
    out = sorted(rows.values(), key=lambda r: -r[key])
    if a.get("worst"):
        out = list(reversed(out))
    return {"period": [start, end], "channel_filter": ch.name if ch else "tümü", "products": out[: int(a.get("limit") or 10)]}


def order_lookup(user, **a):
    from apps.sales.models import SalesOrder
    q = (a.get("query") or "").strip()
    qs = SalesOrder.objects.select_related("channel").order_by("-order_date")
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(external_ref__icontains=q) | Q(customer_name__icontains=q) | Q(customer__name__icontains=q))
    if a.get("status"):
        qs = qs.filter(status=a["status"])
    out = []
    for o in qs[:15]:
        sh = o.shipments.order_by("-id").first() if hasattr(o, "shipments") else None
        out.append({"number": o.number, "date": o.order_date, "channel": o.channel.name, "customer": o.customer_name or str(o.customer or ""),
                    "status": o.get_status_display(), "total_incl_vat": o.grand_total,
                    "carrier": sh.get_carrier_display() if sh and sh.carrier else "", "tracking_no": sh.tracking_no if sh else ""})
    return {"orders": out, "status_codes": dict(SalesOrder.STATUS)}


# ---------------------------------------------------------------- stok
def product_stock(user, **a):
    from apps.catalog.models import Product
    from apps.inventory.models import Quant
    from apps.inventory.services import average_daily_sales, stock_summary
    q = (a.get("query") or "").strip()
    qs = Product.objects.filter(active=True)
    if q:
        qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q) | Q(barcode=q))
    out = []
    for p in qs[:10]:
        s = stock_summary(p)
        row = {"sku": p.sku, "name": p.name, "available": s["available"], "reserved": s.get("reserved", 0),
               "physical": s.get("physical", s["available"]), "incoming": s.get("incoming", 0), "min_stock": p.min_stock}
        if not p.is_kit:
            avg = average_daily_sales(p)
            row["avg_daily_sales_90d"] = avg
            row["days_of_cover"] = int(s["available"] / avg) if avg else None
            row["lots"] = [{"lot": x.lot.lot_no if x.lot else "", "expiry": x.lot.expiry_date if x.lot else None,
                            "location": x.location.code, "qty": x.quantity}
                           for x in Quant.objects.filter(product=p, quantity__gt=0).select_related("lot", "location")
                           .order_by("lot__expiry_date")[:8]]
        out.append(row)
    return {"products": out, "note": "available = satışa uygun (rezerve ve SKT'si geçmiş hariç)"}


def stock_alerts(user, **a):
    from apps.inventory.services import expiring_lots, low_stock_products, purchase_suggestion
    days = int(a.get("expiry_days") or 90)
    low = []
    for p, avail in low_stock_products()[:MAX_ROWS]:
        s = purchase_suggestion(p)
        low.append({"sku": p.sku, "name": p.name, "available": avail, "min_stock": p.min_stock, "suggested_purchase_qty": s["suggested_qty"]})
    exp = [{"sku": l.product.sku, "name": l.product.name, "lot": l.lot_no, "expiry": l.expiry_date,
            "days_left": (l.expiry_date - timezone.localdate()).days, "qty": l.on_hand} for l in expiring_lots(days)[:MAX_ROWS]]
    return {"below_min_stock": low, f"expiring_within_{days}_days": exp}


# ---------------------------------------------------------------- cari / finans
def customer_info(user, **a):
    from apps.partners.models import Partner
    q = (a.get("query") or "").strip()
    out = []
    can_fin = user.has_perm("accounting.view_ledgerentry")
    for p in Partner.objects.filter(Q(name__icontains=q) | Q(code__iexact=q))[:8]:
        row = {"code": p.code, "name": p.name, "type": p.get_kind_display(), "city": p.city}
        if hasattr(p, "sales_orders"):
            orders = p.sales_orders.exclude(status="cancelled")
            row["orders_last_365d"] = orders.filter(order_date__gte=timezone.now() - dt.timedelta(days=365)).count()
            last = orders.order_by("-order_date").first()
            row["last_order"] = {"number": last.number, "date": last.order_date, "total": last.grand_total} if last else None
        if can_fin and apps.is_installed("apps.accounting"):
            from apps.accounting.services import balance
            row["balance"] = balance(p)
            row["credit_limit"] = getattr(p, "credit_limit", None)
        out.append(row)
    return {"customers": out, "note": "balance > 0: müşteri bize borçlu" if can_fin else "Bakiye için muhasebe yetkisi yok"}


def receivables(user, **a):
    from apps.accounting.services import cash_flow, overdue_receivables
    rows = overdue_receivables()
    by = {}
    for r in rows:
        x = by.setdefault(r["invoice"].partner.name, {"customer": r["invoice"].partner.name, "open": Decimal(0), "max_days_overdue": 0, "invoices": 0})
        x["open"] += r["open"]
        x["max_days_overdue"] = max(x["max_days_overdue"], r["days"])
        x["invoices"] += 1
    return {"overdue_total": sum((r["open"] for r in rows), Decimal(0)),
            "overdue_by_customer": sorted(by.values(), key=lambda r: -r["open"]), "cash_flow_next_weeks": cash_flow(6)}


def marketplace_settlements(user, **a):
    from apps.accounting.models import MarketplaceSettlement
    qs = MarketplaceSettlement.objects.select_related("channel").order_by("-period_end")
    ch = _channel(a.get("channel"))
    if ch:
        qs = qs.filter(channel=ch)
    return {"settlements": [{"channel": s.channel.name, "period": [s.period_start, s.period_end], "gross_sales": s.gross_sales,
                             "commission": s.commission, "shipping": s.shipping, "campaign_share": s.campaign_share, "returns": s.returns,
                             "service_fees": s.service_fees, "expected_net": s.expected_net, "bank_received": s.bank_received,
                             "status": s.get_status_display()} for s in qs[:12]]}


def run_report(user, **a):
    from apps.reports.registry import REPORTS
    code = a.get("report")
    rep = REPORTS.get(code)
    if rep is None:
        return {"error": "Bilinmeyen rapor", "available": {k: v["title"] for k, v in REPORTS.items()}}
    if "karlilik" in code and not user.has_perm("accounting.view_invoice"):
        return {"error": "Kârlılık raporları için muhasebe görüntüleme yetkiniz yok."}
    start, end = _period(a)
    data = rep["fn"]({"start": start, "end": end, "days": a.get("days") or 180, "channel": None, "warehouse": None})
    return {"report": rep["title"], "period": [start, end], "columns": [c[1] for c in data["columns"]],
            "rows": [[r.get(k) for k, _, _ in data["columns"]] for r in data["rows"][:30]], "row_count": len(data["rows"]),
            "totals": data.get("totals"), "note": data.get("note")}


def production_status(user, **a):
    from apps.production.models import ProductionOrder
    qs = ProductionOrder.objects.select_related("product", "subcontractor").order_by("-created_at")
    if not a.get("all"):
        qs = qs.filter(status__in=ProductionOrder.OPEN)
    return {"orders": [{"number": o.number, "product": o.product.name, "type": o.get_kind_display(),
                        "subcontractor": str(o.subcontractor or ""), "planned": o.planned_qty, "produced": o.produced_qty,
                        "status": o.get_status_display(), "planned_date": o.planned_date, "unit_cost": o.unit_cost} for o in qs[:20]]}


TOOLS = [
    {"name": "sales_summary", "fn": sales_summary, "perms": ["sales.view_salesorder"], "app": "apps.sales",
     "description": "Tarih aralığında sipariş adedi ve ciro (KDV hariç ve dahil), kanal kırılımıyla. İptaller ve onaylanmamış siparişler ayrı sayılır.",
     "schema": {"type": "object", "properties": {**PERIOD, "channel": {"type": "string", "description": "Kanal kodu/adı: trendyol, hepsiburada, web, bayi..."}}}},
    {"name": "top_products", "fn": top_products, "perms": ["sales.view_salesorder"], "app": "apps.sales",
     "description": "En çok (veya worst=true ile en az) satan ürünler; ciro veya adede göre.",
     "schema": {"type": "object", "properties": {**PERIOD, "channel": {"type": "string"}, "limit": {"type": "integer"},
                                                 "sort": {"type": "string", "enum": ["revenue", "qty"]}, "worst": {"type": "boolean"}}}},
    {"name": "order_lookup", "fn": order_lookup, "perms": ["sales.view_salesorder"], "app": "apps.sales",
     "description": "Sipariş arama: sipariş no, pazaryeri sipariş no veya müşteri adına göre; durum ve kargo takip no.",
     "schema": {"type": "object", "properties": {"query": {"type": "string"}, "status": {"type": "string"}}}},
    {"name": "product_stock", "fn": product_stock, "perms": ["inventory.view_quant"], "app": "apps.inventory",
     "description": "Ürün stok durumu (ad, SKU veya barkodla arama): satışa uygun, rezerve, gelecek, LOT/SKT/lokasyon, günlük satış ortalaması ve kaç gün yeteceği.",
     "schema": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "stock_alerts", "fn": stock_alerts, "perms": ["inventory.view_quant"], "app": "apps.inventory",
     "description": "Minimum stok altındaki ürünler (önerilen satın alma miktarıyla) ve SKT'si yaklaşan LOT'lar.",
     "schema": {"type": "object", "properties": {"expiry_days": {"type": "integer", "description": "Kaç gün içinde SKT'si dolanlar (varsayılan 90)"}}}},
    {"name": "customer_info", "fn": customer_info, "perms": ["partners.view_partner"], "app": "apps.partners",
     "description": "Cari (müşteri/bayi/tedarikçi) bilgisi: son sipariş, yıllık sipariş adedi, bakiye ve kredi limiti (yetki varsa).",
     "schema": {"type": "object", "properties": {"query": {"type": "string", "description": "Cari adı veya kodu"}}, "required": ["query"]}},
    {"name": "receivables", "fn": receivables, "perms": ["accounting.view_invoice"], "app": "apps.accounting",
     "description": "Vadesi geçmiş alacaklar (müşteri bazında) ve önümüzdeki haftaların beklenen tahsilat/ödeme nakit akışı.",
     "schema": {"type": "object", "properties": {}}},
    {"name": "marketplace_settlements", "fn": marketplace_settlements, "perms": ["accounting.view_marketplacesettlement"], "app": "apps.accounting",
     "description": "Pazaryeri hakedişleri: satış, komisyon, kargo, kampanya, iade kesintileri, beklenen net ve bankaya yatan.",
     "schema": {"type": "object", "properties": {"channel": {"type": "string"}}}},
    {"name": "run_report", "fn": run_report, "perms": ["reports.view_report"], "app": "apps.reports",
     "description": "Hazır raporu çalıştırır: stok-yaslandirma, devir-hizi, kanal-karlilik, urun-karlilik, skt.",
     "schema": {"type": "object", "properties": {"report": {"type": "string", "enum": ["stok-yaslandirma", "devir-hizi", "kanal-karlilik", "urun-karlilik", "skt"]},
                                                 **PERIOD, "days": {"type": "integer"}}, "required": ["report"]}},
    {"name": "production_status", "fn": production_status, "perms": ["production.view_productionorder"], "app": "apps.production",
     "description": "Üretim ve fason emirleri: planlanan/üretilen, durum, birim maliyet.",
     "schema": {"type": "object", "properties": {"all": {"type": "boolean", "description": "true: kapananlar dahil"}}}},
]


LABELS = {"sales_summary": "satış özeti", "top_products": "ürün satışları", "order_lookup": "siparişler", "product_stock": "ürün stoğu",
          "stock_alerts": "stok uyarıları", "customer_info": "cari bilgisi", "receivables": "alacaklar", "marketplace_settlements": "hakedişler",
          "run_report": "rapor", "production_status": "üretim emirleri"}


def tools_for(user):
    return [t for t in TOOLS if apps.is_installed(t["app"]) and all(user.has_perm(p) for p in t["perms"])]


def run_tool(user, name, args):
    tool = next((t for t in tools_for(user) if t["name"] == name), None)
    if tool is None:
        return {"error": "Bu veri için yetkiniz yok veya sorgu bulunamadı."}
    try:
        return _clean(tool["fn"](user, **(args or {})))
    except Exception as exc:  # noqa: BLE001 — yapay zekâya hata metni dönülür, sistem çökmez
        return {"error": f"Sorgu çalıştırılamadı: {exc}"}
