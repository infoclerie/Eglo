"""Otomatik işlem logu: ERP modüllerindeki her kayıt değişikliği AuditLog'a yazılır."""
import datetime
import decimal
import uuid

from django.conf import settings
from django.db.models.signals import post_delete, post_save

from .middleware import get_current_user

# Gürültü yapan / teknik kayıtlar işlem geçmişine yazılmaz
SKIP_MODELS = {"core.AuditLog", "core.Sequence", "core.UserPreference", "chat.Presence", "chat.Participant",
               "notifications.Notification", "assistant.AssistantMessage", "integrations.IntegrationJob", "integrations.SyncLog",
               "inventory.Quant", "inventory.Reservation", "inventory.StockMove", "sales.OrderStatusLog"}


def _jsonable(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time, decimal.Decimal, uuid.UUID)):
        return str(value)
    from django.db.models.fields.files import FieldFile
    if isinstance(value, FieldFile):  # dosya alanı (boş dosyada .url hata verir)
        return value.name or ""
    return value


def _snapshot(instance):
    data = {}
    for f in instance._meta.concrete_fields:
        data[f.attname] = _jsonable(getattr(instance, f.attname))
    return data


def _tracked(sender):
    return sender._meta.app_label in settings.ERP_MODULES and sender._meta.label not in SKIP_MODELS


def _write(action, instance):
    from .models import AuditLog
    AuditLog.objects.create(
        user=get_current_user(), action=action, model=instance._meta.label,
        object_id=str(instance.pk), object_repr=str(instance)[:255], data=_snapshot(instance),
    )


def on_save(sender, instance, created, raw=False, **kwargs):
    if raw or not _tracked(sender):
        return
    _write("create" if created else "update", instance)


def on_delete(sender, instance, **kwargs):
    if _tracked(sender):
        _write("delete", instance)


def connect():
    post_save.connect(on_save, dispatch_uid="erp_audit_save")
    post_delete.connect(on_delete, dispatch_uid="erp_audit_delete")
