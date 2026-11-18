"""
CRM iş kuralları (§8.3–8.5).
- Teklif aşamasına geçen fırsat için `crm.quote_followup_days` (varsayılan 3) gün sonra otomatik takip görevi açılır.
- Segment (son 12 ay satışlarına göre, öncelik sırasıyla):
  Potansiyel = hiç siparişi yok · Yeni = ilk siparişi son 30 gün içinde · Uyuyan = son sipariş 90 günden eski ·
  VIP = 12 aylık ciro ≥ `crm.vip_threshold` (varsayılan 250.000) · Düzenli = son 90 günde ≥ 3 sipariş · Diğer = Aktif
"""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.core.events import publish
from apps.core.models import Setting

from .models import Activity, Opportunity

SEGMENTS = {"vip": "VIP", "regular": "Düzenli", "new": "Yeni", "sleeping": "Uzun süredir almayan", "prospect": "Potansiyel",
            "active": "Aktif"}


def move_stage(opp, stage, user=None, lost_reason=""):
    if stage not in dict(Opportunity.STAGES):
        raise ValidationError("Geçersiz aşama.")
    if stage == "lost" and not (lost_reason or opp.lost_reason):
        lost_reason = "Belirtilmedi"
    opp.stage, opp.stage_changed_at = stage, timezone.now()
    if lost_reason:
        opp.lost_reason = lost_reason
    opp.probability = {"lead": 10, "contacted": 20, "needs": 35, "quoted": 50, "negotiation": 70, "won": 100, "lost": 0}[stage]
    opp.save()
    if stage == "quoted":
        days = int(Setting.get("crm.quote_followup_days", 3))
        Activity.objects.create(kind="task", subject=f"Teklif takibi: {opp.name}", opportunity=opp, partner=opp.partner,
                                due_date=timezone.localdate() + timedelta(days=days), owner=opp.owner or user,
                                notes=f"Teklif gönderildi. {days} gün içinde dönüş yoksa arayın.")
    publish("crm.stage_changed", opportunity=opp, stage=stage, user=user)
    return opp


def due_activities(user=None, today=None):
    today = today or timezone.localdate()
    qs = Activity.objects.filter(done=False, due_date__lte=today).select_related("partner", "opportunity")
    return qs.filter(Q(owner=user) | Q(owner__isnull=True)) if user is not None else qs


def segment_rows(today=None):
    from apps.partners.models import Partner
    today = today or timezone.localdate()
    year_ago, q90 = today - timedelta(days=365), today - timedelta(days=90)
    vip = Decimal(str(Setting.get("crm.vip_threshold", 250000)))
    valid = ~Q(sales_orders__status="cancelled")
    rows = []
    for p in (Partner.objects.filter(kind__in=["customer", "both"], active=True)
              .annotate(first=Min("sales_orders__order_date", filter=valid), last=Max("sales_orders__order_date", filter=valid),
                        revenue=Sum("sales_orders__grand_total", filter=valid & Q(sales_orders__order_date__date__gte=year_ago)),
                        recent=Count("sales_orders", filter=valid & Q(sales_orders__order_date__date__gte=q90)))):
        rev = p.revenue or Decimal(0)
        if p.last is None:
            seg = "prospect"
        elif p.first.date() >= today - timedelta(days=30):
            seg = "new"
        elif p.last.date() < q90:
            seg = "sleeping"
        elif rev >= vip:
            seg = "vip"
        elif p.recent >= 3:
            seg = "regular"
        else:
            seg = "active"
        rows.append({"partner": p, "segment": seg, "label": SEGMENTS[seg], "revenue": rev, "last": p.last, "recent": p.recent})
    return rows
