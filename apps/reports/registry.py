"""
Rapor tanımları. Yeni rapor: bir fonksiyon yazıp REPORTS'a ekleyin.
Fonksiyon (params) → {"columns": [(anahtar, başlık, tür)], "rows": [dict], "totals": dict, "chart": {...}|None, "note": str}
Tür: text | int | qty | money | pct | date
"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

ZERO = Decimal("0")
AGE_BUCKETS = [(30, "0–30 gün"), (90, "31–90 gün"), (180, "91–180 gün"), (365, "181–365 gün"), (10 ** 6, "365+ gün")]


def stock_aging(p):
    """Stok yaşlandırma: LOT'un depoya giriş tarihine göre eldeki stok (adet ve maliyet değeri)."""
    from apps.inventory.models import Quant
    today = timezone.localdate()
    by = defaultdict(lambda: defaultdict(lambda: ZERO))
    qs = Quant.objects.filter(quantity__gt=0).exclude(location__kind__in=("supplier", "customer", "production", "adjustment", "scrap")).select_related("product", "lot")
    if p.get("warehouse"):
        qs = qs.filter(location__warehouse_id=p["warehouse"])
    for q in qs:
        received = (q.lot.received_at.date() if q.lot else (q.created_at.date() if getattr(q, "created_at", None) else today))
        age = (today - received).days
        label = next(l for limit, l in AGE_BUCKETS if age <= limit)
        r = by[q.product]
        r[label] += q.quantity
        r["total"] += q.quantity
        r["value"] += q.quantity * q.product.cost
        r["age_sum"] += q.quantity * age
    rows = []
    for prod, r in sorted(by.items(), key=lambda x: -x[1]["value"]):
        row = {"sku": prod.sku, "name": prod.name, **{l: r[l] for _, l in AGE_BUCKETS}, "total": r["total"],
               "avg_age": int(r["age_sum"] / r["total"]) if r["total"] else 0, "value": r["value"].quantize(Decimal("0.01"))}
        rows.append(row)
    cols = [("sku", "SKU", "text"), ("name", "Ürün", "text")] + [(l, l, "qty") for _, l in AGE_BUCKETS] + [
        ("total", "Toplam", "qty"), ("avg_age", "Ort. yaş (gün)", "int"), ("value", "Stok değeri (₺)", "money")]
    totals = {k: sum((r[k] for r in rows), ZERO) for k in [l for _, l in AGE_BUCKETS] + ["total", "value"]}
    chart = {"type": "bar", "labels": [l for _, l in AGE_BUCKETS], "data": [float(totals[l]) for _, l in AGE_BUCKETS],
             "title": "Yaşa göre stok (adet)"}
    return {"columns": cols, "rows": rows, "totals": totals, "chart": chart,
            "note": "Yaş = LOT'un depoya giriş tarihinden bugüne geçen gün. Değer = adet × ortalama maliyet."}


def turnover(p):
    """Stok devir hızı ve stokta kalma süresi (dönem içi satış çıkışlarına göre)."""
    from apps.catalog.models import Product
    from apps.inventory.models import StockMove
    from apps.inventory.services import stock_summary
    start, end = p["start"], p["end"]
    days = max((end - start).days + 1, 1)
    moves = StockMove.objects.filter(date__date__gte=start, date__date__lte=end)
    out = dict(moves.filter(move_type__in=("sale_out", "production_consume")).values_list("product").annotate(s=Sum("quantity")))
    inn = dict(moves.filter(move_type__in=("purchase_in", "production_in", "customer_return")).values_list("product").annotate(s=Sum("quantity")))
    rows = []
    for prod in Product.objects.filter(active=True).exclude(kind="kit"):
        now = stock_summary(prod)["physical"]
        sold = out.get(prod.pk, ZERO)
        begin = now + sold - inn.get(prod.pk, ZERO)
        avg = (begin + now) / 2
        rate = (sold / avg) if avg > 0 else ZERO
        daily = sold / days
        cover = int(now / daily) if daily > 0 else None
        status = "Durgun" if sold == 0 and now > 0 else ("Hızlı" if cover is not None and cover < 30 else ("Yavaş" if cover is not None and cover > 180 else "Normal"))
        if now == 0 and sold == 0:
            continue
        rows.append({"sku": prod.sku, "name": prod.name, "sold": sold, "stock": now, "avg_stock": avg.quantize(Decimal("0.01")),
                     "rate": rate.quantize(Decimal("0.01")), "cover": cover if cover is not None else "—", "status": status,
                     "value": (now * prod.cost).quantize(Decimal("0.01"))})
    rows.sort(key=lambda r: (-r["rate"], r["name"]))
    cols = [("sku", "SKU", "text"), ("name", "Ürün", "text"), ("sold", "Dönem çıkışı", "qty"), ("stock", "Eldeki stok", "qty"),
            ("avg_stock", "Ortalama stok", "qty"), ("rate", "Devir hızı", "qty"), ("cover", "Kaç gün yeter", "text"),
            ("status", "Durum", "text"), ("value", "Stok değeri (₺)", "money")]
    stagnant = [r for r in rows if r["status"] == "Durgun"]
    return {"columns": cols, "rows": rows, "totals": {"sold": sum((r["sold"] for r in rows), ZERO), "value": sum((r["value"] for r in rows), ZERO)},
            "chart": None, "note": (f"Devir hızı = dönem çıkışı ÷ ortalama stok · Kaç gün yeter = eldeki stok ÷ günlük ortalama çıkış ({days} gün). "
                                    f"Dönemde hiç çıkışı olmayan {len(stagnant)} ürün 'Durgun'.")}


def product_profit(p):
    from apps.accounting.services import product_profitability
    from apps.catalog.models import SalesChannel
    ch = SalesChannel.objects.filter(pk=p["channel"]).first() if p.get("channel") else None
    data = product_profitability(p["start"], p["end"], ch)
    rows = [{"sku": r["product"].sku, "name": r["product"].name, "qty": r["qty"], "revenue": r["revenue"],
             "product_cost": r["product_cost"], "fees": sum((r.get(k, ZERO) for k in ("extra_cost", "commission", "shipping", "service", "ads", "pos")), ZERO),
             "contribution": r["contribution"], "margin_pct": r["margin_pct"]} for r in data]
    cols = [("sku", "SKU", "text"), ("name", "Ürün", "text"), ("qty", "Adet", "qty"), ("revenue", "Ciro (KDV hariç)", "money"),
            ("product_cost", "Ürün maliyeti", "money"), ("fees", "Kanal giderleri", "money"), ("contribution", "Katkı kârı", "money"),
            ("margin_pct", "Kâr marjı %", "pct")]
    totals = {k: sum((r[k] for r in rows), ZERO) for k in ("qty", "revenue", "product_cost", "fees", "contribution")}
    totals["margin_pct"] = (totals["contribution"] / totals["revenue"] * 100).quantize(Decimal("0.01")) if totals["revenue"] else ZERO
    top = rows[:10]
    return {"columns": cols, "rows": rows, "totals": totals,
            "chart": {"type": "bar", "labels": [r["name"][:22] for r in top], "data": [float(r["contribution"]) for r in top], "title": "En kârlı 10 ürün (₺)"},
            "note": "Kanal giderleri: komisyon, kargo, hizmet bedeli, reklam, POS ve ek maliyetler (Muhasebe › Kanal maliyet profilleri)."}


def channel_profit(p):
    from apps.accounting.services import product_profitability
    from apps.catalog.models import SalesChannel
    rows = []
    for ch in SalesChannel.objects.all():
        data = product_profitability(p["start"], p["end"], ch)
        if not data:
            continue
        rev = sum((r["revenue"] for r in data), ZERO)
        cost = sum((r["product_cost"] for r in data), ZERO)
        fees = sum((sum((r.get(k, ZERO) for k in ("extra_cost", "commission", "shipping", "service", "ads", "pos")), ZERO) for r in data), ZERO)
        contrib = sum((r["contribution"] for r in data), ZERO)
        rows.append({"channel": ch.name, "qty": sum((r["qty"] for r in data), ZERO), "revenue": rev, "product_cost": cost, "fees": fees,
                     "contribution": contrib, "margin_pct": (contrib / rev * 100).quantize(Decimal("0.01")) if rev else ZERO})
    rows.sort(key=lambda r: -r["contribution"])
    cols = [("channel", "Kanal", "text"), ("qty", "Satılan adet", "qty"), ("revenue", "Ciro (KDV hariç)", "money"),
            ("product_cost", "Ürün maliyeti", "money"), ("fees", "Kanal giderleri", "money"), ("contribution", "Katkı kârı", "money"),
            ("margin_pct", "Kâr marjı %", "pct")]
    totals = {k: sum((r[k] for r in rows), ZERO) for k in ("qty", "revenue", "product_cost", "fees", "contribution")}
    totals["margin_pct"] = (totals["contribution"] / totals["revenue"] * 100).quantize(Decimal("0.01")) if totals["revenue"] else ZERO
    return {"columns": cols, "rows": rows, "totals": totals,
            "chart": {"type": "doughnut", "labels": [r["channel"] for r in rows], "data": [float(r["revenue"]) for r in rows], "title": "Kanallara göre ciro"},
            "note": "Sevk edilmiş siparişler esas alınır. Pazaryeri kesintilerinin gerçekleşeni için Muhasebe › Pazaryeri hakedişleri."}


def expiry(p):
    """SKT raporu: yaklaşan ve geçmiş son kullanma tarihli stoklar."""
    from apps.inventory.models import Quant
    from apps.inventory.services import expiry_status
    today = timezone.localdate()
    days = int(p.get("days") or 180)
    rows = []
    for q in (Quant.objects.filter(quantity__gt=0, lot__expiry_date__lte=today + dt.timedelta(days=days)).exclude(location__kind__in=("supplier", "customer", "production", "adjustment", "scrap"))
              .select_related("product", "lot", "location").order_by("lot__expiry_date")):
        rows.append({"sku": q.product.sku, "name": q.product.name, "lot": q.lot.lot_no, "expiry": q.lot.expiry_date,
                     "left": (q.lot.expiry_date - today).days, "location": q.location.code, "qty": q.quantity,
                     "value": (q.quantity * q.product.cost).quantize(Decimal("0.01")),
                     "status": {"expired": "Geçmiş", "critical": "Kritik", "warning": "Uyarı", "info": "Bilgi"}.get(expiry_status(q.lot), "Normal")})
    cols = [("sku", "SKU", "text"), ("name", "Ürün", "text"), ("lot", "LOT", "text"), ("expiry", "SKT", "date"), ("left", "Kalan gün", "int"),
            ("location", "Lokasyon", "text"), ("qty", "Adet", "qty"), ("value", "Değer (₺)", "money"), ("status", "Durum", "text")]
    return {"columns": cols, "rows": rows, "totals": {"qty": sum((r["qty"] for r in rows), ZERO), "value": sum((r["value"] for r in rows), ZERO)},
            "chart": None, "note": f"Önümüzdeki {days} gün içinde SKT'si dolan veya geçmiş stoklar."}


REPORTS = {
    "stok-yaslandirma": {"title": "Stok yaşlandırma", "desc": "Ürünler depoda ne kadar süredir bekliyor? Yaş grubuna göre adet ve değer.",
                         "fn": stock_aging, "params": ["warehouse"], "icon": "box"},
    "devir-hizi": {"title": "Stok devir hızı", "desc": "Hangi ürün hızlı dönüyor, hangisi durgun? Eldeki stok kaç gün yeter?",
                   "fn": turnover, "params": ["period"], "icon": "chart"},
    "kanal-karlilik": {"title": "Kanal kârlılığı", "desc": "Trendyol, Hepsiburada, web, bayi... her kanalın cirosu, giderleri ve katkı kârı.",
                       "fn": channel_profit, "params": ["period"], "icon": "cart"},
    "urun-karlilik": {"title": "Ürün kârlılığı", "desc": "Ürün bazında ciro, maliyet, kanal giderleri ve kâr marjı.",
                      "fn": product_profit, "params": ["period", "channel"], "icon": "chart"},
    "skt": {"title": "SKT raporu", "desc": "Son kullanma tarihi yaklaşan ve geçmiş LOT'lar, lokasyonlarıyla.",
            "fn": expiry, "params": ["days"], "icon": "alert"},
}
