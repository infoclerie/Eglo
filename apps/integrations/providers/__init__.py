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
    presets: list = []  # isteğe bağlı hazır servis kartları (bkz. notify.MAIL_PRESETS)
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

    def periodic(self, account):
        """Periyodik işler: [(tür, referans, veri, aralık_dakika)]"""
        return []


class ComingSoon(Provider):
    available = False
    steps = []


_REGISTRY = {}


def _load():
    if _REGISTRY:
        return _REGISTRY
    from .notify import NetgsmSms, SmtpEmail
    from .ai import ClaudeAI, OpenAIAI
    from .hepsiburada import Hepsiburada
    from .ikas import Ikas
    from .trendyol import Trendyol
    from .uyumsoft import UyumsoftEInvoice
    items = [UyumsoftEInvoice(), Trendyol(), Hepsiburada(), Ikas(), SmtpEmail(), NetgsmSms(), ClaudeAI(), OpenAIAI()]
    for code, name, cat, color, icon, desc in [
        ("amazon", "Amazon", "marketplace", "#232f3e", "cart", "Sipariş ve stok senkronu"),
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


CATEGORY_LABELS = {"ai": "Yapay zekâ asistanı", "einvoice": "e-Fatura / e-Arşiv", "notify_email": "Bildirim — e-posta", "notify_sms": "Bildirim — SMS", "marketplace": "Pazaryerleri", "ecommerce": "E-ticaret",
                   "cargo": "Kargo", "bank": "Banka"}
