"""Onay akışı servisi. Kullanım: bkz. apps/core/MODULE.md"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .events import publish
from .models import ApprovalRequest


def request_approval(action, obj, title, user=None, payload=None):
    existing = ApprovalRequest.objects.filter(
        action=action, target_model=obj._meta.label, target_id=str(obj.pk), status="pending"
    ).first()
    if existing:
        return existing
    req = ApprovalRequest.objects.create(
        action=action, title=title, target_model=obj._meta.label, target_id=str(obj.pk),
        payload=payload or {}, requested_by=user,
    )
    publish("approval.requested", request=req)
    return req


def _check_decider(req, user):
    if user is None or not (user.is_superuser or user.has_perm("core.decide_approval")):
        raise PermissionDenied("Bu talebi onaylama yetkiniz yok.")
    if req.status != "pending":
        raise ValidationError("Bu talep zaten sonuçlandırılmış.")
    if req.requested_by_id and req.requested_by_id == user.pk and not user.is_superuser:
        raise PermissionDenied("Kendi talebinizi onaylayamazsınız.")


@transaction.atomic
def approve(req, user, note=""):
    req = ApprovalRequest.objects.select_for_update().get(pk=req.pk)
    _check_decider(req, user)
    req.status, req.decided_by, req.decided_at, req.note = "approved", user, timezone.now(), note
    req.save()
    publish(f"approval.approved.{req.action}", request=req, user=user)
    return req


@transaction.atomic
def reject(req, user, note=""):
    req = ApprovalRequest.objects.select_for_update().get(pk=req.pk)
    _check_decider(req, user)
    req.status, req.decided_by, req.decided_at, req.note = "rejected", user, timezone.now(), note
    req.save()
    publish(f"approval.rejected.{req.action}", request=req, user=user)
    return req
