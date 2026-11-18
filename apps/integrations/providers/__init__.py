"""
Sağlayıcı kayıt sistemi. Yeni bir entegrasyon eklemek için:
1. `providers/<ad>.py` içinde `Provider` sınıfından türetin (alanlar, test_connection, handle).
2. Aşağıdaki `_load()` listesine ekleyin. Sihirbaz alanları otomatik form olarak gösterir.
"""
from dataclasses import dataclass, field


@dataclass
class Field:
    name: str
    label: str
    step: str = "credentials"  # credentials | company | settings
    kind: str = "text"  # text | password | choice | bool | int | email
    required: bool = True
    secret: bool = False
    help: str = ""
    default: object = ""
    choices: list = field(default_factory=list)


class Provider:
    code = ""
    name = ""
    category = ""  # einvoice | marketplace | cargo | bank | ecommerce
    description = ""
    color = "#5b3a6e"
    icon = "plug"
    available = True
    fields: list = []
    steps = [("credentials", "Bağlantı bilgileri"), ("company", "Şirket bilgileri"), ("test", "Bağlantı testi"),
             ("settings", "Ayarlar"), ("summary", "Özet ve etkinleştir")]

    def fields_for(self, step):
        return [f for f in self.fields if f.step == step]

    def test_connection(self, config, secrets, environment):
        """Döner: (başarılı_mı, mesaj)"""
        raise NotImplementedError

    def on_activate(self, account):
        """Etkinleştirilince çalışır (ör. muhasebe ayarlarını yazmak)."""

    def handle(self, account, job):
        """Kuyruktaki işi yürütür; hata durumunda istisna fırlatır. Döner: sonuç sözlüğü."""
        raise NotImplementedError

    def on_final_failure(self, account, job, error):
        """Tüm denemeler bitince çağrılır."""


class ComingSoon(Provider):
    available = False
    steps = []


_REGISTRY = {}


def _load():
    if _REGISTRY:
        return _REGISTRY
    from .uyumsoft import UyumsoftEInvoice
    items = [UyumsoftEInvoice()]
    for code, name, cat, color, icon, desc in [
        ("trendyol", "Trendyol", "marketplace", "#f27a1a", "cart", "Sipariş, stok, fiyat, iade ve hakediş senkronu"),
        ("hepsiburada", "Hepsiburada", "marketplace", "#ff6000", "cart", "Sipariş, stok, fiyat, iade"),
        ("amazon", "Amazon", "marketplace", "#232f3e", "cart", "Sipariş ve stok senkronu"),
        ("website", "Web sitesi", "ecommerce", "#2563c9", "cart", "Web sitesi siparişleri ve stok"),
        ("yurtici", "Yurtiçi Kargo", "cargo", "#1d4ed8", "truck", "Etiket, takip numarası, teslim durumu"),
        ("aras", "Aras Kargo", "cargo", "#d71920", "truck", "Etiket, takip numarası, teslim durumu"),
        ("mng", "MNG Kargo", "cargo", "#0b5394", "truck", "Etiket, takip numarası, teslim durumu"),
        ("bank", "Banka hesap hareketleri", "bank", "#128a52", "chart", "Hesap hareketleri ve mutabakat"),
    ]:
        p = ComingSoon()
        p.code, p.name, p.category, p.color, p.icon, p.description = code, name, cat, color, icon, desc
        items.append(p)
    for p in items:
        _REGISTRY[p.code] = p
    return _REGISTRY


def all_providers():
    return list(_load().values())


def get_provider(code):
    return _load().get(code)


CATEGORY_LABELS = {"einvoice": "e-Fatura / e-Arşiv", "marketplace": "Pazaryerleri", "ecommerce": "E-ticaret",
                   "cargo": "Kargo", "bank": "Banka"}
