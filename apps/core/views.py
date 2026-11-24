import json
import re
from importlib import import_module

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import theme
from .models import Setting, UserPreference


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower().translate(str.maketrans("çğıöşüâî", "cgiosuai"))).strip("-")


def collect_widgets(request):
    """Her açık modülün `dashboard.py` → `widgets(request)` kartları; her karta kalıcı bir anahtar verilir."""
    widgets = []
    for code in settings.ERP_MODULES:
        try:
            mod = import_module(f"apps.{code}.dashboard")
        except ModuleNotFoundError:
            continue
        for w in mod.widgets(request):
            w.setdefault("key", f"{code}.{_slug(w['title'])}")
            widgets.append(w)
    return widgets


def collect_charts(request):
    charts = []
    for code in settings.ERP_MODULES:
        try:
            mod = import_module(f"apps.{code}.dashboard")
        except ModuleNotFoundError:
            continue
        if hasattr(mod, "charts"):
            charts.extend(mod.charts(request))
    return charts


@login_required
def rates(request):
    from .rates import get_rates
    return JsonResponse({"rates": get_rates()})


@login_required
def dashboard(request):
    if hasattr(request.user, "portal") and not request.user.is_staff:
        return redirect("portal:home")  # bayi kullanıcıları doğrudan portala
    pref = UserPreference.for_user(request.user)
    items = collect_charts(request) + collect_widgets(request)
    for i in items:
        i["is_chart"] = "type" in i
    if pref.widget_order:
        order = {k: n for n, k in enumerate(pref.widget_order)}
        items.sort(key=lambda w: order.get(w["key"], 999))
    hidden = set(pref.hidden_widgets or [])
    visible = [w for w in items if w["key"] not in hidden]
    from django.apps import apps as _apps
    ai_enabled = _apps.is_installed("apps.assistant") and request.user.has_perm("assistant.add_assistantmessage")
    ai_suggestions = []
    if ai_enabled:
        from apps.assistant.services import suggestions
        ai_suggestions = suggestions(request.user)[:3]
    return render(request, "core/dashboard.html", {"ai_enabled": ai_enabled, "ai_suggestions": ai_suggestions,
        "charts": [w for w in visible if w["is_chart"]], "widgets": [w for w in visible if not w["is_chart"]],
        "catalog": items, "hidden_keys": json.dumps(sorted(hidden)),
        "chart_json": json.dumps([{k: w[k] for k in ("key", "type", "labels", "data")} for w in visible if w["is_chart"]])})


@login_required
@require_POST
def save_layout(request):
    """Ana panel düzeni (sürükle-bırak): {"apps": [...], "widgets": [...], "hidden": [...]}"""
    try:
        data = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"ok": False}, status=400)
    pref = UserPreference.for_user(request.user)
    for field, key in (("app_order", "apps"), ("widget_order", "widgets"), ("hidden_widgets", "hidden")):
        if isinstance(data.get(key), list):
            setattr(pref, field, [str(x)[:80] for x in data[key]][:100])
    if data.get("reset"):
        pref.app_order, pref.widget_order, pref.hidden_widgets = [], [], []
    pref.save()
    return JsonResponse({"ok": True})


@login_required
def appearance(request):
    pref = UserPreference.for_user(request.user)
    if request.method == "POST":
        color = request.POST.get("color", "")
        if request.POST.get("action") == "reset":
            pref.sidebar_color = ""
            messages.success(request, "Varsayılan renge dönüldü.")
        elif theme.valid(color):
            pref.sidebar_color = color
            if request.POST.get("for_all") and request.user.is_superuser:
                Setting.put("ui.default_color", color, "Tüm kullanıcılar için varsayılan menü rengi")
                messages.success(request, "Renk kaydedildi ve tüm kullanıcılar için varsayılan yapıldı.")
            else:
                messages.success(request, "Menü rengi kaydedildi.")
        else:
            messages.error(request, "Geçerli bir renk seçin.")
        pref.save()
        return redirect("core:appearance")
    return render(request, "core/appearance.html", {"presets": theme.PRESETS, "pref": pref})


# ---------------------------------------------------------------- yedekler (yalnız süper kullanıcı)
from django.contrib.auth.decorators import user_passes_test  # noqa: E402
from django.core.exceptions import ValidationError as _VE  # noqa: E402
from django.http import FileResponse  # noqa: E402

from . import backups as bk  # noqa: E402

superuser_required = user_passes_test(lambda u: u.is_active and u.is_superuser)


def _tr_upper(s):
    """Türkçe büyük harf: i→İ, ı→I ('geri dön' → 'GERİ DÖN')."""
    return (s or "").strip().replace("i", "İ").replace("ı", "I").upper().replace("İ", "I")  # İngilizce klavye de kabul


@login_required
@superuser_required
def backups(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create":
                name = bk.create_backup(request.POST.get("name") or "Elle alınan yedek", request.user)
                messages.success(request, f"Yedek alındı: {name}")
            elif action == "upload" and request.FILES.get("file"):
                messages.success(request, f"Yedek dosyası eklendi: {bk.save_upload(request.FILES['file'])}. Geri dönmek için listeden seçin.")
            elif action == "delete":
                bk.delete_backup(request.POST.get("file"))
                messages.success(request, "Yedek silindi.")
            elif action == "restore":
                if _tr_upper(request.POST.get("confirm")) != "GERI DÖN":
                    raise _VE("Onay için kutuya GERİ DÖN yazın.")
                res = bk.restore_backup(request.POST.get("file"), user=request.user)
                for w in res["warnings"]:
                    messages.warning(request, w)
                messages.success(request, f"Sistem '{res['meta'].get('name')}' yedeğine döndü. Dönüş öncesi hali de yedeklendi "
                                          f"({res['safety']}). Güvenlik için tüm oturumlar kapandı; yeniden giriş yapın.")
                return redirect("login")
            elif action == "reset":
                if _tr_upper(request.POST.get("confirm")) != "TEMIZLE":
                    raise _VE("Onay için kutuya TEMİZLE yazın.")
                res = bk.reset_test_data(request.POST.getlist("groups"), request.user)
                total = sum(res["counts"].values())
                detail = ", ".join(f"{k}: {v}" for k, v in res["counts"].items() if v)
                messages.success(request, f"{total} kayıt silindi ({detail or 'silinecek kayıt yoktu'}). Öncesi yedeklendi: {res['safety']}")
        except _VE as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("core:backups")
    import shutil
    usage = shutil.disk_usage(bk.root())
    groups = bk.reset_groups()
    return render(request, "core/backups.html", {"items": bk.list_backups(), "test_groups": [g for g in groups if g["kind"] == "test"],
                                                 "master_groups": [g for g in groups if g["kind"] == "master"],
                                                 "free_gb": round(usage.free / 1024 ** 3, 1)})


@login_required
@superuser_required
def backup_download(request, filename):
    try:
        path = bk._path(filename)
    except _VE:
        from django.http import Http404
        raise Http404
    return FileResponse(path.open("rb"), as_attachment=True, filename=filename)


@login_required
def activity(request):
    """Tüm işlemlerin geçmişi (kayıt değişikliği, entegrasyon, stok, sipariş) — filtre ve Excel."""
    import datetime as dt

    from django.contrib.auth.models import User
    from django.core.exceptions import PermissionDenied
    from django.utils import timezone

    from . import activity as act
    if not (request.user.is_superuser or request.user.has_perm("core.view_auditlog")):
        raise PermissionDenied
    today = timezone.localdate()

    def d(key, default):
        try:
            return dt.date.fromisoformat(request.GET.get(key, ""))
        except ValueError:
            return default
    start, end = d("start", today - dt.timedelta(days=6)), d("end", today)
    source, q = request.GET.get("kaynak", ""), request.GET.get("q", "").strip()
    user_id = request.GET.get("kullanici") or None
    rows = act.collect(start, end, q, user_id, source, {"account": request.GET.get("baglanti")})
    if request.GET.get("format") == "xlsx":
        from django.http import HttpResponse
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "İşlem geçmişi"
        ws.append(["Zaman", "Kaynak", "Kullanıcı", "İşlem", "Açıklama", "Ayrıntı"])
        for r in rows:
            ws.append([timezone.localtime(r["at"]).replace(tzinfo=None), act.SOURCES.get(r["source"], r["source"]), str(r["user"] or "sistem"),
                       r["action"], r["text"], r.get("detail", "")])
        resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="islem_gecmisi_{today:%Y%m%d}.xlsx"'
        wb.save(resp)
        return resp
    return render(request, "core/activity.html", {"rows": rows, "start": start, "end": end, "source": source, "q": q,
                                                  "user_id": user_id, "sources": act.SOURCES, "users": User.objects.order_by("username"),
                                                  "limit": act.LIMIT})


def _device(ua):
    ua = ua or ""
    os_ = next((n for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
                                ("Mac OS", "Mac"), ("Linux", "Linux")) if k in ua), "Bilinmiyor")
    br = next((n for k, n in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Chrome/", "Chrome"), ("Firefox/", "Firefox"), ("Safari/", "Safari")) if k in ua), "")
    return f"{br} · {os_}".strip(" ·")


@login_required
@superuser_required
def active_users(request):
    """Aktif kullanıcılar: son görülme, IP adresi, cihaz, son sayfa. Yeşil = son 5 dakikada işlem yaptı."""
    import datetime as dt

    from django.utils import timezone

    from .models import UserActivity
    hours = int(request.GET.get("saat") or 24)
    now = timezone.now()
    rows = []
    for a in UserActivity.objects.select_related("user").filter(last_seen__gte=now - dt.timedelta(hours=hours)).order_by("-last_seen"):
        mins = int((now - a.last_seen).total_seconds() // 60)
        rows.append({"a": a, "online": mins < 5, "mins": mins, "device": _device(a.user_agent)})
    return render(request, "core/active_users.html", {"rows": rows, "hours": hours,
                                                      "online": sum(1 for r in rows if r["online"])})


@login_required
@superuser_required
def ai_context(request):
    """Yapay zekâ için proje rehberi (.md) — tüm dokümanlar + canlı özet, gizli bilgi yok."""
    from django.http import HttpResponse
    from django.utils import timezone

    from .context_pack import build_pack
    resp = HttpResponse(build_pack(), content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="EGLO_ERP_PROJE_REHBERI_{timezone.localdate():%Y%m%d}.md"'
    return resp
