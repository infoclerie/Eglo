"""
Modül listesi — ERP'ye modül EKLEMEK / ÇIKARMAK için tek yer.

- Bir modülü açmak: listeye ekle, sonra `python manage.py migrate`.
- Bir modülü kapatmak: listeden çıkar. Bağımlı modül varsa sistem açılışta hata verir.
- Ortam değişkeni ile de verilebilir:  ERP_MODULES=core,catalog,inventory
- `core` her zaman açıktır.

Her modül `apps/<kod>/module.py` içinde MANIFEST tanımlar (ad, sürüm, bağımlılıklar).
"""
import os

DEFAULT_MODULES = [
    "core",
    "catalog",
    "inventory",
    "partners",
    "sales",
    "shipping",
    "purchase",
    "accounting",
    "integrations",
    "portal",
    "crm",
    "notifications",
    "chat",
    "production",
    "reports",
    "imports",
    "assistant",
]


def enabled_modules():
    raw = os.environ.get("ERP_MODULES")
    mods = [m.strip() for m in raw.split(",") if m.strip()] if raw else list(DEFAULT_MODULES)
    if "core" not in mods:
        mods.insert(0, "core")
    return mods
