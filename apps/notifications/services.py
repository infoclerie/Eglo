"""
Bildirim motoru. `notify(olay, alanlar, url="", musteri=None, once_key=None)`
- Olayın aktif kurallarındaki taslaklar {alan} değerleriyle doldurulur.
- Personel kuralı: rol kullanıcılarına sistem içi + (açıksa) e-posta / SMS.
- Müşteri kuralı: `musteri={"email","phone","ref"}` adresine e-posta / SMS (bilgilendirme amaçlı).
- E-posta / SMS, Entegrasyonlar'da kurulu aktif e-posta / SMS bağlantısı üzerinden kuyrukla gönderilir.
- `once_key`: aynı anahtarla günde bir kez (kritik stok tekrar etmesin).
"""
import re

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.core.models import Setting

from .events import EVENTS
from .models import Notification, NotificationRule


class _Safe(dict):
    def __missing__(self, key):
        return ""


def render(text, fields):
    ctx = _Safe({"firma": (Setting.get("accounting.company", {}) or {}).get("title") or "Eglo Kozmetik"})
    ctx.update({k: ("" if v is None else v) for k, v in fields.items()})
    try:
        return (text or "").format_map(ctx)
    except (ValueError, IndexError):
        return text or ""


def normalize_phone(p):
    digits = re.sub(r"\D", "", p or "")
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 and digits.startswith("5") else ""


def _queue(channel, to, subject, body, ref):
    try:
        from apps.integrations.services import active_account, enqueue
    except ImportError:
        return None
    acc = active_account(f"notify_{channel}")
    if acc is None or not to:
        return None
    kind = "notify.email" if channel == "email" else "notify.sms"
    payload = {"to": to, "subject": subject, "body": body} if channel == "email" else {"to": to, "text": body[:600]}
    return enqueue(acc, kind, ref[:100], payload, key=f"{acc.pk}:{kind}:{to}:{ref}:{timezone.now().timestamp()}")


def notify(event, fields, url="", customer=None, once_key=None):
    if once_key:
        ck = f"notify:{event}:{once_key}:{timezone.localdate()}"
        if cache.get(ck):
            return 0
        cache.set(ck, 1, 86400)
    sent = 0
    for rule in NotificationRule.objects.filter(event=event, active=True).select_related("group"):
        subject, body, sms = render(rule.subject, fields), render(rule.body, fields), render(rule.sms_text, fields)
        ref = f"{event}:{fields.get('siparis_no') or fields.get('fatura_no') or fields.get('cari_kodu') or ''}"
        if rule.audience == "customer":
            if customer:
                if rule.email:
                    sent += bool(_queue("email", customer.get("email"), subject, body, ref))
                if rule.sms:
                    sent += bool(_queue("sms", normalize_phone(customer.get("phone")), subject, sms, ref))
            continue
        User = get_user_model()
        users = User.objects.filter(groups=rule.group, is_active=True) if rule.group_id else User.objects.filter(is_superuser=True, is_active=True)
        for u in users:
            if rule.in_app:
                Notification.objects.create(user=u, event=event, title=subject[:200], body=body, url=url)
                sent += 1
            if rule.email and u.email:
                sent += bool(_queue("email", u.email, subject, f"{body}\n\n{url}", f"{ref}:{u.pk}"))
            if rule.sms and hasattr(u, "contact") and u.contact.mobile:
                sent += bool(_queue("sms", normalize_phone(u.contact.mobile), subject, sms, f"{ref}:{u.pk}"))
    return sent


DEFAULT_STAFF = [("order_new", "E-ticaret ekibi"), ("order_cancelled", "Satış ekibi"), ("approval_requested", None),
                 ("low_stock", "Depo müdürü"), ("low_stock", "Satın alma"), ("integration_failed", None)]


def ensure_default_rules():
    """Eksik kuralları varsayılan taslaklarla oluşturur. Müşteri bildirimleri KAPALI başlar (kullanıcı açar)."""
    from django.contrib.auth.models import Group
    created = 0
    for code, ev in EVENTS.items():
        groups = [g for e, g in DEFAULT_STAFF if e == code] if ev["audience"] == "staff" else [None]
        for gname in groups or [None]:
            g = Group.objects.get_or_create(name=gname)[0] if gname else None
            _, new = NotificationRule.objects.get_or_create(event=code, group=g, defaults={
                "in_app": ev["audience"] == "staff", "email": False, "sms": False, "active": ev["audience"] == "staff",
                "subject": ev["subject"], "body": ev["body"], "sms_text": ev["sms"]})
            created += new
    return created
