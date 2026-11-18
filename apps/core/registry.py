"""
Modül kayıt sistemi.

Her modül `apps/<kod>/module.py` içinde şu sözlüğü tanımlar:

    MANIFEST = {
        "code": "inventory",
        "name": "Depo ve Stok",
        "version": "0.1.0",
        "depends": ["core", "catalog"],
        "menu": [("Stok Özeti", "inventory:summary")],   # isteğe bağlı
        "urls": "apps.inventory.urls",                    # isteğe bağlı
    }

Açık modüller config/modules.py'den gelir. Açılışta bağımlılıklar kontrol edilir.
"""
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path


def load_manifests():
    manifests = {}
    for code in settings.ERP_MODULES:
        try:
            mod = import_module(f"apps.{code}.module")
        except ModuleNotFoundError as exc:
            raise ImproperlyConfigured(f"Modül bulunamadı: apps/{code}/module.py") from exc
        manifest = dict(mod.MANIFEST)
        if manifest.get("code") != code:
            raise ImproperlyConfigured(f"apps/{code}/module.py içindeki code alanı '{code}' olmalı")
        manifests[code] = manifest
    return manifests


def check_dependencies(manifests=None):
    manifests = manifests or load_manifests()
    errors = []
    for code, m in manifests.items():
        for dep in m.get("depends", []):
            if dep not in manifests:
                errors.append(f"'{code}' modülü '{dep}' modülüne bağımlı ama '{dep}' kapalı.")
    if errors:
        raise ImproperlyConfigured("Modül bağımlılık hatası:\n" + "\n".join(errors))
    return manifests


def module_urlpatterns():
    patterns = []
    for code, m in load_manifests().items():
        if code != "core" and m.get("urls"):
            patterns.append(path(f"{code}/", include((m["urls"], code), namespace=code)))
    return patterns


def is_enabled(code):
    return code in settings.ERP_MODULES
