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
                              "active": active})
        if items:
            nav.append({"code": m["code"], "name": m["name"], "icon": m.get("icon", "box"),
                        "color": m.get("color", "#5b3a6e"), "items": items})
    user = getattr(request, "user", None)
    from .models import UserPreference
    from .theme import current
    pref = UserPreference.objects.filter(user=user).first() if getattr(user, "is_authenticated", False) else None
    if pref and pref.app_order:
        order = {code: i for i, code in enumerate(pref.app_order)}
        nav.sort(key=lambda g: order.get(g["code"], 999))
    return {"erp_nav": nav, "ui_theme": current(user), "ui_pref": pref}
