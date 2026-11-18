from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from . import approvals
from .models import ApprovalRequest, AuditLog, Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "description")
    search_fields = ("key",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("at", "user", "action", "model", "object_id", "object_repr")
    list_filter = ("action", "model")
    search_fields = ("object_repr", "object_id", "model")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("requested_at", "title", "action", "status", "requested_by", "decided_by")
    list_filter = ("status", "action")
    readonly_fields = [f.name for f in ApprovalRequest._meta.fields if f.name != "note"]
    actions = ["do_approve", "do_reject"]

    def has_add_permission(self, request):
        return False

    def _decide(self, request, queryset, fn, label):
        ok = 0
        for req in queryset:
            try:
                fn(req, request.user)
                ok += 1
            except (PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{req}: {exc}", messages.ERROR)
        if ok:
            self.message_user(request, f"{ok} talep {label}.", messages.SUCCESS)

    @admin.action(description="Seçili talepleri ONAYLA")
    def do_approve(self, request, queryset):
        self._decide(request, queryset, approvals.approve, "onaylandı")

    @admin.action(description="Seçili talepleri REDDET")
    def do_reject(self, request, queryset):
        self._decide(request, queryset, approvals.reject, "reddedildi")
