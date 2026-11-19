"""
İşlem geçmişi: tüm modüllerin kayıtları tek listede.
Çekirdek kendi kayıt değişikliklerini (AuditLog) verir; diğer modüller 'core.collect_activity' olayına satır döndürür:
  handler(start, end, q, user_id, source, extra) → [{"at", "source", "user", "action", "text", "detail", "url", "level"}]
Böylece çekirdek diğer modülleri bilmeden hepsini gösterir (modül kapalıysa satırları da gelmez).
"""
from django.apps import apps
from django.db.models import Q

from .events import publish
from .models import AuditLog

LIMIT = 300
SOURCES = {"kayit": "Kayıt değişikliği", "entegrasyon": "Entegrasyon", "stok": "Stok hareketi", "siparis": "Sipariş durumu"}
ACTION_LABEL = dict(AuditLog.ACTIONS)


def _model_label(label):
    try:
        return apps.get_model(label)._meta.verbose_name.capitalize()
    except (LookupError, ValueError):
        return label


def audit_rows(start, end, q, user_id):
    qs = AuditLog.objects.select_related("user").filter(at__date__gte=start, at__date__lte=end)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if q:
        qs = qs.filter(Q(object_repr__icontains=q) | Q(model__icontains=q))
    return [{"at": a.at, "source": "kayit", "user": a.user, "action": ACTION_LABEL.get(a.action, a.action),
             "text": f"{_model_label(a.model)}: {a.object_repr}", "detail": "", "level": "danger" if a.action == "delete" else ""}
            for a in qs[:LIMIT]]


def collect(start, end, q="", user_id=None, source="", extra=None):
    rows = []
    if source in ("", "kayit"):
        rows += audit_rows(start, end, q, user_id)
    for part in publish("core.collect_activity", start=start, end=end, q=q, user_id=user_id, source=source, extra=extra or {}):
        rows += part or []
    rows.sort(key=lambda r: r["at"], reverse=True)
    return rows[:LIMIT]
