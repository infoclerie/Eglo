"""
Sanal ofis: şirketi departmanlara ayırır, her departmanın CANLI ERP verisini toplar.
Her departman: kod, ad, renk, çalışanlar (rol grubundaki gerçek kullanıcılar; yoksa varsayılan unvanlar), iş yükü,
göstergeler [(etiket, değer, bağlantı, uyarı?)], son işler [(metin, bağlantı)], animasyon ipucu (moving: kişi yürüsün mü).
Modül kapalıysa o departman gösterilmez. Yeni departman: DEPARTMENTS listesine bir fonksiyon ekleyin.
"""
import datetime as dt
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import Sum
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.formats import tl


def _url(name, *args):
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return ""


def _staff(groups, defaults, extra=0):
    """Gruptaki aktif kullanıcılar (en fazla 5); yoksa varsayılan unvanlar. extra: iş yüküne göre ek varsayılan kişi."""
    users = list(User.objects.filter(is_active=True, groups__name__in=groups).distinct().order_by("username")[:5])
    if users:
        from apps.core.models import UserActivity
        seen = {a.user_id: a.last_seen for a in UserActivity.objects.filter(user__in=users)}
        now = timezone.now()
        return [{"name": u.get_full_name() or u.username, "real": True,
                 "online": bool(seen.get(u.pk) and (now - seen[u.pk]).total_seconds() < 300)} for u in users]
    n = min(len(defaults), max(1, len(defaults) - 1 + min(extra, 1)))
    return [{"name": t, "real": False, "online": False} for t in defaults[:n]]


def _m(label, value, url="", warn=False):
    return {"label": label, "value": value, "url": url, "warn": bool(warn)}


def management(today):
    from apps.core.models import ApprovalRequest
    m, load = [], 0
    pend = ApprovalRequest.objects.filter(status="pending").count()
    m.append(_m("Onay bekleyen", pend, _url("admin:core_approvalrequest_changelist"), pend))
    if apps.is_installed("apps.sales"):
        from apps.sales.models import SalesOrder
        q = SalesOrder.objects.filter(order_date__date=today).exclude(status="cancelled")
        m.insert(0, _m("Bugünkü ciro (KDV dahil)", tl(q.aggregate(s=Sum("grand_total"))["s"] or 0), _url("sales:pool")))
        m.insert(1, _m("Bugünkü sipariş", q.count(), _url("sales:pool")))
    load = pend
    return {"code": "yonetim", "name": "Yönetim", "color": "#7c3aed", "load": load, "metrics": m,
            "staff": _staff(["Şirket yöneticisi"], ["Genel müdür"]), "items": []}


def sales(today):
    if not apps.is_installed("apps.sales"):
        return None
    from apps.sales.models import SalesOrder
    qs = SalesOrder.objects.select_related("channel")
    new = qs.filter(status="new").count()
    b2b = qs.filter(order_date__date=today, channel__code__in=["bayi", "b2b", "eczane", "kurumsal"]).count()
    m = [_m("Bugün gelen sipariş", qs.filter(order_date__date=today).count(), _url("sales:pool")),
         _m("Stok ayrılamayan (yeni)", new, _url("sales:pool"), new), _m("Bayi / kurumsal (bugün)", b2b, _url("sales:pool"))]
    if apps.is_installed("apps.crm"):
        from apps.crm.models import Opportunity
        m.append(_m("Açık fırsat (CRM)", Opportunity.objects.exclude(stage__in=["won", "lost"]).count(), _url("crm:board")))
    if apps.is_installed("apps.chat"):
        pass
    items = [{"text": f"{o.number} · {o.channel.name} · {o.customer_name[:24]} · {o.get_status_display()}",
              "url": _url("admin:sales_salesorder_change", o.pk)} for o in qs.order_by("-order_date")[:6]]
    load = qs.filter(order_date__date=today).count()
    return {"code": "satis", "name": "Satış", "color": "#e11d48", "load": load, "metrics": m, "items": items,
            "staff": _staff(["Satış ekibi"], ["Satış temsilcisi", "Bayi sorumlusu", "Saha satış"], load // 10)}


def ecommerce(today):
    """Her aktif pazaryeri / e-ticaret bağlantısı ayrı masa: Trendyolcu, Hepsiburadacı, ikasçı..."""
    if not apps.is_installed("apps.integrations"):
        return []
    from apps.integrations.models import ExternalOrder, IntegrationAccount
    out = []
    colors = {"trendyol": "#f27a1a", "hepsiburada": "#ff6000", "ikas": "#5b4ff5"}
    titles = {"trendyol": "Trendyol sorumlusu", "hepsiburada": "Hepsiburada sorumlusu", "ikas": "Web (ikas) sorumlusu"}
    users = _staff(["E-ticaret ekibi"], [])
    for i, acc in enumerate(IntegrationAccount.objects.filter(active=True).order_by("name")):
        p = acc.provider_obj
        if not p or p.category not in ("marketplace", "ecommerce"):
            continue
        last = acc.jobs.exclude(status="pending").order_by("-created_at").first()
        failed = acc.jobs.filter(status="failed").count()
        n = ExternalOrder.objects.filter(account=acc, created_at__date=today).count()
        person = users[i % len(users)] if users else {"name": titles.get(acc.provider, f"{acc.name} sorumlusu"), "real": False, "online": False}
        recent = acc.external_orders.select_related("order").order_by("-created_at")[:5]
        out.append({"code": f"kanal-{acc.pk}", "group": "eticaret", "name": acc.name, "color": colors.get(acc.provider, p.color or "#0ea5e9"),
                    "load": n, "staff": [person],
                    "metrics": [_m("Bugün gelen sipariş", n, _url("integrations:channel", acc.pk)),
                                _m("Son güncelleme", timezone.localtime(last.finished_at or last.created_at).strftime("%H:%M") if last else "—",
                                   _url("integrations:channel", acc.pk)),
                                _m("Başarısız iş", failed, _url("integrations:jobs") + "?status=failed", failed),
                                _m("Eşleşen ürün", acc.listings.count(), _url("integrations:listings", acc.pk))],
                    "items": [{"text": f"{e.order.number} · {e.external_id} · {e.order.get_status_display()}",
                               "url": _url("admin:sales_salesorder_change", e.order_id)} for e in recent if e.order_id]})
    return out


def warehouse(today):
    if not apps.is_installed("apps.inventory"):
        return None
    from apps.inventory import services as inv
    from apps.inventory.models import Quant, StockCount, StockMove
    low = len(inv.low_stock_products())
    exp = len(inv.expiring_lots(90))
    units = Quant.objects.filter(location__is_sellable=True).aggregate(s=Sum("quantity"))["s"] or 0
    moves_today = StockMove.objects.filter(date__date=today).count()
    counts = StockCount.objects.filter(status__in=["draft", "submitted"]).count()
    m = [_m("Satışa uygun toplam adet", f"{int(units):,}".replace(",", "."), _url("inventory:summary")),
         _m("Kritik stok ürün", low, _url("inventory:summary") + "?kritik=1", low),
         _m("90 gün içinde SKT", exp, _url("reports:show", "skt") if apps.is_installed("apps.reports") else "", exp),
         _m("Bugünkü stok hareketi", moves_today, _url("core:activity") + "?kaynak=stok"), _m("Açık sayım", counts, _url("admin:inventory_stockcount_changelist"))]
    items = [{"text": f"{x.get_move_type_display()} · {x.product.sku} × {x.quantity.normalize():f} · {x.destination.code}", "url": ""}
             for x in StockMove.objects.select_related("product", "destination").order_by("-date")[:6]]
    return {"code": "depo", "name": "Depo", "color": "#0d9488", "load": moves_today, "metrics": m, "items": items, "moving": moves_today > 0,
            "staff": _staff(["Depo müdürü", "Depo personeli"], ["Depo şefi", "Depocu", "Forklift operatörü"], moves_today // 20)}


def shipping(today):
    if not apps.is_installed("apps.shipping"):
        return None
    from apps.shipping.models import ReturnRequest, Shipment
    qs = Shipment.objects
    waiting = qs.filter(status__in=["waiting", "picking"]).count()
    packed = qs.filter(status__in=["picked", "packed"]).count()
    shipped = qs.filter(shipped_at__date=today).count()
    returns = ReturnRequest.objects.exclude(status__in=["completed", "rejected"]).count()
    m = [_m("Toplanacak", waiting, _url("shipping:queue"), waiting > 20), _m("Paketlendi, kargo bekliyor", packed, _url("shipping:queue")),
         _m("Bugün kargoya verilen", shipped, _url("shipping:queue")), _m("Açık iade", returns, _url("admin:shipping_returnrequest_changelist"), returns)]
    items = [{"text": f"{s.number} · {s.order.number} · {s.get_status_display()}" + (f" · {s.tracking_no}" if s.tracking_no else ""),
              "url": _url("shipping:pick", s.pk)} for s in qs.select_related("order").order_by("-id")[:6]]
    return {"code": "kargo", "name": "Sevkiyat ve Kargo", "color": "#d97706", "load": waiting + packed, "metrics": m, "items": items,
            "moving": waiting + packed > 0, "staff": _staff(["Sevkiyat personeli"], ["Toplayıcı", "Paketleyici", "Kargo sorumlusu"], (waiting + packed) // 10)}


def purchase(today):
    if not apps.is_installed("apps.purchase"):
        return None
    from apps.purchase.models import PurchaseOrder, PurchaseRequest
    open_ = PurchaseOrder.objects.filter(status__in=PurchaseOrder.OPEN)
    late = open_.filter(expected_date__lt=today).count()
    appr = PurchaseOrder.objects.filter(status="approval").count()
    reqs = PurchaseRequest.objects.filter(status="open").count()
    m = [_m("Açık satın alma siparişi", open_.count(), _url("admin:purchase_purchaseorder_changelist")),
         _m("Onay bekleyen", appr, _url("admin:core_approvalrequest_changelist"), appr), _m("Termini geçen", late, _url("admin:purchase_purchaseorder_changelist"), late),
         _m("Açık talep", reqs, _url("admin:purchase_purchaserequest_changelist"))]
    items = [{"text": f"{o.number} · {o.supplier} · {o.get_status_display()}", "url": _url("admin:purchase_purchaseorder_change", o.pk)}
             for o in PurchaseOrder.objects.select_related("supplier").order_by("-id")[:6]]
    return {"code": "satinalma", "name": "Satın Alma", "color": "#a16207", "load": open_.count() + reqs, "metrics": m, "items": items,
            "staff": _staff(["Satın alma"], ["Satın alma uzmanı", "Tedarik planlama"], reqs // 5)}


def accounting(today):
    if not apps.is_installed("apps.accounting"):
        return None
    from apps.accounting.models import Invoice
    from apps.accounting.services import overdue_receivables
    inv = Invoice.objects
    today_n = inv.filter(issue_date=today, direction="out").count()
    err = inv.filter(status__in=["error", "ready"], direction="out").count()
    over = sum((r["open"] for r in overdue_receivables()), Decimal(0))
    incoming = inv.filter(direction="in", issue_date__gte=today - dt.timedelta(days=7)).count()
    m = [_m("Bugün kesilen fatura", today_n, _url("accounting:invoices")), _m("Gönderilmeyi / düzeltilmeyi bekleyen", err, _url("accounting:invoices"), err),
         _m("Vadesi geçmiş alacak", tl(over), _url("accounting:balances"), over > 0), _m("Son 7 gün gelen fatura", incoming, _url("accounting:invoices"))]
    items = [{"text": f"{i.number or 'Taslak'} · {(i.buyer_title if i.direction == 'out' else str(i.partner or ''))[:24]} · {i.get_status_display()}",
              "url": _url("accounting:invoice", i.pk)} for i in inv.order_by("-id")[:6]]
    return {"code": "muhasebe", "name": "Finans ve Muhasebe", "color": "#15803d", "load": today_n + err, "metrics": m, "items": items,
            "staff": _staff(["Muhasebe", "Finans"], ["Muhasebeci", "Finans uzmanı"], err // 5)}


def production(today):
    if not apps.is_installed("apps.production"):
        return None
    from apps.production.models import ProductionOrder
    qs = ProductionOrder.objects
    running = qs.filter(status__in=["in_progress", "at_subcontractor"]).count()
    qc = qs.filter(status="qc").count()
    m = [_m("Üretimde / fasonda", running, _url("production:list")), _m("Kalite kontrol bekleyen", qc, _url("production:list") + "?durum=qc", qc),
         _m("Açık emir", qs.filter(status__in=ProductionOrder.OPEN).count(), _url("production:list"))]
    items = [{"text": f"{o.number} · {o.product.name[:28]} · {o.get_status_display()}", "url": _url("production:detail", o.pk)}
             for o in qs.select_related("product").order_by("-id")[:6]]
    return {"code": "uretim", "name": "Üretim ve Kalite", "color": "#9333ea", "load": running + qc, "metrics": m, "items": items,
            "moving": running > 0, "staff": _staff(["Üretim sorumlusu"], ["Üretim şefi", "Kalite kontrol", "Operatör"], running)}


DEPARTMENTS = [management, sales, warehouse, shipping, purchase, accounting, production]


def snapshot():
    today = timezone.localdate()
    out = []
    for fn in DEPARTMENTS:
        try:
            d = fn(today)
        except Exception as exc:  # noqa: BLE001 — bir departman hatası ofisi düşürmesin
            d = {"code": fn.__name__, "name": fn.__name__, "color": "#64748b", "load": 0, "staff": [],
                 "metrics": [_m("Veri alınamadı", str(exc)[:80], "", True)], "items": []}
        if d:
            out.append(d)
    try:
        out += ecommerce(today)
    except Exception:  # noqa: BLE001
        pass
    return {"at": timezone.localtime().strftime("%H:%M:%S"), "departments": out}
