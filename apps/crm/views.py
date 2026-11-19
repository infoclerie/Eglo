import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Activity, Opportunity


@login_required
@permission_required("crm.view_opportunity", raise_exception=True)
def board(request):
    cols = []
    opps = Opportunity.objects.select_related("partner", "owner")
    if request.GET.get("mine"):
        opps = opps.filter(owner=request.user)
    for code, label in Opportunity.STAGES:
        items = [o for o in opps if o.stage == code]
        cols.append({"code": code, "label": label, "items": items, "total": sum(o.expected_amount for o in items)})
    return render(request, "crm/board.html", {"cols": cols})


@login_required
@permission_required("crm.change_opportunity", raise_exception=True)
@require_POST
def move(request):
    data = json.loads(request.body or "{}")
    opp = get_object_or_404(Opportunity, pk=data.get("id"))
    try:
        services.move_stage(opp, data.get("stage"), request.user)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": " ".join(exc.messages)}, status=400)
    return JsonResponse({"ok": True})


@login_required
@permission_required("crm.view_activity", raise_exception=True)
def activities(request):
    if request.method == "POST" and request.user.has_perm("crm.change_activity"):
        Activity.objects.filter(pk=request.POST.get("done")).update(done=True)
        messages.success(request, "Takip tamamlandı.")
        return redirect(request.get_full_path())
    due = services.due_activities(request.user)
    upcoming = Activity.objects.filter(done=False).exclude(pk__in=due).select_related("partner", "opportunity")[:100]
    return render(request, "crm/activities.html", {"due": due, "upcoming": upcoming})


@login_required
@permission_required("crm.view_opportunity", raise_exception=True)
def segments(request):
    rows = services.segment_rows()
    seg = request.GET.get("s")
    counts = {}
    for r in rows:
        counts[r["segment"]] = counts.get(r["segment"], 0) + 1
    if seg:
        rows = [r for r in rows if r["segment"] == seg]
    return render(request, "crm/segments.html", {"rows": rows, "seg": seg, "counts": counts, "labels": services.SEGMENTS})


# ---------------------------------------------------------------- kampanyalar
from django import forms  # noqa: E402

from .models import Campaign  # noqa: E402


class CampaignForm(forms.ModelForm):
    segments = forms.MultipleChoiceField(choices=list(services.SEGMENTS.items()), required=False, label="Segmentler",
                                         widget=forms.CheckboxSelectMultiple,
                                         help_text="Hiçbiri seçilmezse tüm müşterilere (izinli olanlara) gider.")

    class Meta:
        model = Campaign
        fields = ["name", "channel", "segments", "city", "recipient_type", "subject", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 7})}

    def clean(self):
        d = super().clean()
        if d.get("channel") == "email" and not d.get("subject"):
            self.add_error("subject", "E-posta kampanyasında konu zorunlu.")
        return d


@login_required
@permission_required("crm.view_campaign", raise_exception=True)
def campaigns(request):
    return render(request, "crm/campaigns.html", {"items": Campaign.objects.all()[:200]})


@login_required
@permission_required("crm.add_campaign", raise_exception=True)
def campaign_edit(request, pk=None):
    obj = get_object_or_404(Campaign, pk=pk) if pk else None
    if obj and obj.status == "sent":
        messages.error(request, "Gönderilmiş kampanya düzenlenemez.")
        return redirect("crm:campaign", pk=obj.pk)
    form = CampaignForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        c = form.save()
        return redirect("crm:campaign", pk=c.pk)
    return render(request, "crm/campaign_edit.html", {"form": form, "obj": obj})


@login_required
@permission_required("crm.view_campaign", raise_exception=True)
def campaign_detail(request, pk):
    c = get_object_or_404(Campaign, pk=pk)
    if request.method == "POST" and request.user.has_perm("crm.change_campaign"):
        try:
            base = request.build_absolute_uri("/").rstrip("/")
            if request.POST.get("test_to"):
                services.send_campaign(c, base, request.user, test_to=request.POST["test_to"].strip())
                messages.success(request, "Deneme iletisi gönderim kuyruğuna alındı.")
            elif request.POST.get("send"):
                r = services.send_campaign(c, base, request.user)
                messages.success(request, f"{r['queued']} alıcı gönderim kuyruğuna alındı; {r['skipped']} cari atlandı (izin / iletişim yok).")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("crm:campaign", pk=pk)
    if c.status == "sent":
        rows = [(r.partner, r.to, r.status, r.get_status_display()) for r in c.recipients.select_related("partner")]
    else:
        labels = dict(c.recipients.model.STATUS)
        rows = [(p, to, st, labels[st]) for p, to, st in services.audience(c)]
    counts = {k: sum(1 for r in rows if r[2] == k) for k in ("queued", "no_consent", "no_contact")}
    sample = rows[0][0] if rows else None
    return render(request, "crm/campaign.html", {
        "c": c, "rows": rows[:500], "total": len(rows), "counts": counts,
        "preview_subject": services.fill(c.subject, sample) if sample else c.subject,
        "preview_body": services.fill(c.body, sample) if sample else c.body,
        "seg_labels": [services.SEGMENTS.get(s, s) for s in c.segments]})


def unsubscribe(request, token):
    """Herkese açık: e-postadaki bağlantıyla ticari ileti izni geri alınır (giriş gerekmez)."""
    from django.core import signing
    from django.utils import timezone

    from apps.partners.models import Partner
    try:
        data = signing.loads(token, salt="crm.unsubscribe", max_age=60 * 60 * 24 * 365 * 2)
    except signing.BadSignature:
        return render(request, "crm/unsubscribe.html", {"ok": False}, status=400)
    p = Partner.objects.filter(pk=data["p"]).first()
    if p and request.method == "POST":
        setattr(p, "consent_email" if data["c"] == "email" else "consent_sms", False)
        p.consent_date = timezone.now()
        p.save(update_fields=["consent_email", "consent_sms", "consent_date"])
        return render(request, "crm/unsubscribe.html", {"ok": True, "done": True})
    return render(request, "crm/unsubscribe.html", {"ok": bool(p), "partner": p})
