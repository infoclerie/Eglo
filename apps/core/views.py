from importlib import import_module

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def collect_widgets(request):
    """Her açık modülün `dashboard.py` → `widgets(request)` fonksiyonundan kartları toplar."""
    widgets = []
    for code in settings.ERP_MODULES:
        try:
            mod = import_module(f"apps.{code}.dashboard")
        except ModuleNotFoundError:
            continue
        widgets.extend(mod.widgets(request))
    return widgets


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {"widgets": collect_widgets(request)})
