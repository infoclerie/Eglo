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


# ---------------------------------------------------------------- kampanyalar (ticari ileti, İYS)
class _Safe(dict):
    def __missing__(self, key):
        return ""


def fill(text, partner):
    from apps.core.models import Setting
    ctx = _Safe(musteri=partner.name, cari_kodu=partner.code,
                firma=(Setting.get("accounting.company", {}) or {}).get("title") or "Eglo Kozmetik")
    try:
        return (text or "").format_map(ctx)
    except (ValueError, IndexError):
        return text or ""


def tr_lower(s):
    """Türkçe küçük harf: İ→i, I→ı (Python'un lower() 'İzmir'i 'i̇zmir' yapar)."""
    return (s or "").strip().replace("İ", "i").replace("I", "ı").lower()


def unsubscribe_token(partner, channel):
    from django.core import signing
    return signing.dumps({"p": partner.pk, "c": channel}, salt="crm.unsubscribe")


def audience(campaign):
    """Hedef kitle: [(cari, adres|"", durum)] — durum: queued | no_consent | no_contact"""
    from apps.notifications.services import normalize_phone
    rows = segment_rows()
    if campaign.segments:
        rows = [r for r in rows if r["segment"] in campaign.segments]
    out = []
    for r in rows:
        p = r["partner"]
        if campaign.city and tr_lower(p.city) != tr_lower(campaign.city):
            continue
        if campaign.channel == "email":
            to, ok = (p.email or "").strip(), p.consent_email
        else:
            to, ok = normalize_phone(p.phone), p.consent_sms
        out.append((p, to, "no_contact" if not to else ("queued" if ok else "no_consent")))
    return out


def send_campaign(campaign, base_url, user=None, test_to=None):
    """
    Kampanyayı gönderim kuyruğuna alır (entegrasyon işçisi gönderir). İzinsiz / iletişimsiz cariler atlanır ve kaydedilir.
    test_to verilirse yalnız o adrese tek bir deneme iletisi gönderir.
    """
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.urls import reverse

    from apps.integrations.services import active_account, enqueue

    from .models import CampaignRecipient
    acc = active_account(f"notify_{campaign.channel}")
    if acc is None:
        raise ValidationError(f"{campaign.get_channel_display()} bağlantısı kurulmamış (Entegrasyonlar › Yeni bağlantı).")
    kind = "notify.email" if campaign.channel == "email" else "notify.sms"

    def payload(partner, to):
        body = fill(campaign.body, partner)
        if campaign.channel == "email":
            url = base_url + reverse("crm:unsubscribe", args=[unsubscribe_token(partner, "email")])
            return {"to": to, "subject": fill(campaign.subject, partner),
                    "body": f"{body}\n\n—\nBu e-postayı ticari ileti izniniz olduğu için aldınız. Almak istemiyorsanız: {url}",
                    "unsubscribe": url}
        return {"to": to, "text": body, "iysfilter": campaign.recipient_type}

    if test_to:
        from apps.partners.models import Partner
        sample = Partner(name="Örnek Müşteri", code="C0000")
        enqueue(acc, kind, f"kampanya {campaign.pk} deneme", payload(sample, test_to) | ({"iysfilter": ""} if campaign.channel == "sms" else {}),
                key=f"camp:{campaign.pk}:test:{test_to}:{timezone.now().timestamp()}")
        return {"queued": 1, "skipped": 0}
    if campaign.status == "sent":
        raise ValidationError("Bu kampanya zaten gönderildi. Yeniden göndermek için kopyalayın.")
    queued = skipped = 0
    with transaction.atomic():
        for partner, to, status in audience(campaign):
            CampaignRecipient.objects.update_or_create(campaign=campaign, partner=partner, defaults={"to": to, "status": status})
            if status != "queued":
                skipped += 1
                continue
            enqueue(acc, kind, f"kampanya {campaign.pk} · {partner.code}", payload(partner, to),
                    key=f"camp:{campaign.pk}:{partner.pk}")
            queued += 1
        campaign.status, campaign.sent_at, campaign.sent_by = "sent", timezone.now(), user
        campaign.queued, campaign.skipped = queued, skipped
        campaign.save()
    return {"queued": queued, "skipped": skipped}
