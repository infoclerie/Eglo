from .registry import load_manifests


def erp(request):
    manifests = load_manifests()
    menu = []
    for m in manifests.values():
        for label, url_name in m.get("menu", []):
            menu.append({"module": m["name"], "label": label, "url_name": url_name})
    return {"erp_modules": manifests.values(), "erp_menu": menu}
