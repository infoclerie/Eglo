from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import Notification


@login_required
def list_view(request):
    if request.method == "POST":
        request.user.notifications.filter(read=False).update(read=True)
        return redirect(request.path)
    return render(request, "notifications/list.html", {"items": request.user.notifications.all()[:200]})


@login_required
def api(request):
    """Zil: okunmamış sayısı + son 8 bildirim. POST {id} → okundu."""
    if request.method == "POST":
        request.user.notifications.filter(pk=request.POST.get("id")).update(read=True)
    qs = request.user.notifications.all()
    return JsonResponse({"unread": qs.filter(read=False).count(),
                         "items": [{"id": n.id, "title": n.title, "body": n.body, "url": n.url, "read": n.read,
                                    "at": n.created_at.strftime("%d.%m %H:%M")} for n in qs[:8]]})


from django import forms  # noqa: E402
from django.contrib import messages  # noqa: E402
from django.contrib.auth.decorators import permission_required  # noqa: E402
from django.shortcuts import get_object_or_404  # noqa: E402

from .events import EVENTS  # noqa: E402
from .models import NotificationRule  # noqa: E402
from .services import ensure_default_rules, render as render_text  # noqa: E402

PERM = "notifications.change_notificationrule"


@login_required
@permission_required(PERM, raise_exception=True)
def center(request):
    """Bildirim merkezi: olay × kanal anahtarları; taslak düzenleme bağlantısı."""
    ensure_default_rules()
    if request.method == "POST":
        rule = get_object_or_404(NotificationRule, pk=request.POST.get("rule"))
        field = request.POST.get("field")
        if field in ("in_app", "email", "sms", "active"):
            setattr(rule, field, request.POST.get("value") == "1")
            rule.save(update_fields=[field])
        return JsonResponse({"ok": True})
    from apps.integrations.services import active_account
    rules = list(NotificationRule.objects.select_related("group"))
    return render(request, "notifications/center.html", {
        "customer": [r for r in rules if r.audience == "customer"], "staff": [r for r in rules if r.audience == "staff"],
        "has_email": bool(active_account("notify_email")), "has_sms": bool(active_account("notify_sms"))})


class RuleForm(forms.ModelForm):
    class Meta:
        model = NotificationRule
        fields = ["active", "in_app", "email", "sms", "group", "subject", "body", "sms_text"]
        widgets = {"body": forms.Textarea(attrs={"rows": 9}), "sms_text": forms.Textarea(attrs={"rows": 3})}


@login_required
@permission_required(PERM, raise_exception=True)
def edit_rule(request, pk):
    rule = get_object_or_404(NotificationRule, pk=pk)
    ev = EVENTS.get(rule.event, {})
    form = RuleForm(request.POST or None, instance=rule)
    if rule.audience == "customer":
        form.fields.pop("group")
        form.fields.pop("in_app")
    if request.method == "POST" and form.is_valid():
        if request.POST.get("action") == "reset":
            rule.subject, rule.body, rule.sms_text = ev["subject"], ev["body"], ev["sms"]
            rule.save()
            messages.success(request, "Varsayılan taslağa dönüldü.")
        else:
            form.save()
            messages.success(request, "Bildirim kaydedildi.")
        return redirect("notifications:edit", pk=rule.pk)
    sample = {k: f"[{v}]" for k, v in ev.get("fields", {}).items()}
    sample.update({"musteri": "Ayşe Yılmaz", "siparis_no": "SIP-000123", "tutar": "1.250,00", "fatura_no": "EGA2026000000045",
                   "takip_no": "YK123456789", "kargo": "Yurtiçi Kargo", "cari_kodu": "C-000017"})
    return render(request, "notifications/edit.html", {
        "rule": rule, "ev": ev, "form": form,
        "preview": {"subject": render_text(rule.subject, sample), "body": render_text(rule.body, sample), "sms": render_text(rule.sms_text, sample)}})
