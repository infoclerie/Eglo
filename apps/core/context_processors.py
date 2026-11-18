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
    return {"erp_nav": nav}
