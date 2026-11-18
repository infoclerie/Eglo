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


@login_required
def dashboard(request):
    if hasattr(request.user, "portal") and not request.user.is_staff:
        return redirect("portal:home")  # bayi kullanıcıları doğrudan portala
    pref = UserPreference.for_user(request.user)
    widgets = collect_widgets(request)
    if pref.widget_order:
        order = {k: i for i, k in enumerate(pref.widget_order)}
        widgets.sort(key=lambda w: order.get(w["key"], 999))
    hidden = set(pref.hidden_widgets or [])
    return render(request, "core/dashboard.html", {
        "widgets": [w for w in widgets if w["key"] not in hidden],
        "hidden": [w for w in widgets if w["key"] in hidden],
        "hidden_keys": json.dumps([w["key"] for w in widgets if w["key"] in hidden])})


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
