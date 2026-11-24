from django.urls import NoReverseMatch, reverse

from .registry import load_manifests


def _safe_reverse(name):
    try:
        return reverse(name)
    except NoReverseMatch:  # bağlı modül kapalıysa menü öğesi gizlenir
        return None


def erp(request):
    """Kenar menüsü: her açık modülün MANIFEST['menu'] öğeleri (etiket, url adı, ikon)."""
    path = getattr(request, "path", "")
    nav = []
    for m in load_manifests().values():
        items = []
        for entry in m.get("menu", []):
            label, url_name = entry[0], entry[1]
            url = _safe_reverse(url_name)
            if url:
                active = url != "/" and path.startswith(url.split("?")[0]) or (url == "/" and path == "/")
                items.append({"label": label, "url": url, "icon": entry[2] if len(entry) > 2 else m.get("icon", "box"),
                              "active": active, "new_tab": len(entry) > 3 and entry[3] == "new_tab"})
        if items:
            nav.append({"code": m["code"], "name": m["name"], "icon": m.get("icon", "box"),
                        "color": m.get("color", "#5b3a6e"), "items": items})
    user = getattr(request, "user", None)
    # Modüllerin dinamik menü grupları: MANIFEST["nav_hook"] = "paket.modul.fonksiyon" → fonksiyon(request) → [grup]
    from importlib import import_module
    for m in load_manifests().values():
        hook = m.get("nav_hook")
        if hook and getattr(user, "is_authenticated", False):
            mod, fn = hook.rsplit(".", 1)
            try:
                for g in getattr(import_module(mod), fn)(request) or []:
                    g.setdefault("color", m.get("color", "#5b3a6e"))
                    for it in g["items"]:
                        it.setdefault("active", path.startswith(it["url"]))
                    nav.append(g)
            except Exception:  # noqa: BLE001 — menü hatası sayfayı düşürmesin
                pass
    from .models import UserPreference
    from .theme import current
    pref = UserPreference.objects.filter(user=user).first() if getattr(user, "is_authenticated", False) else None
    if pref and pref.app_order:
        order = {code: i for i, code in enumerate(pref.app_order)}
        nav.sort(key=lambda g: order.get(g["code"], 999))
    return {"erp_nav": nav, "ui_theme": current(user), "ui_pref": pref}
