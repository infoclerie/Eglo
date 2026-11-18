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


# ---------------------------------------------------------------- tüm yönetim ekranları için ortak davranış
from django.utils.text import capfirst  # noqa: E402

from .field_help import FIELD_HELP  # noqa: E402

_orig_formfield = admin.ModelAdmin.formfield_for_dbfield
_orig_changelist = admin.ModelAdmin.changelist_view
_orig_changeform = admin.ModelAdmin.changeform_view
_orig_inline_formfield = admin.options.InlineModelAdmin.formfield_for_dbfield


def _with_help(formfield, db_field):
    if formfield is not None and not formfield.help_text and db_field.name in FIELD_HELP:
        formfield.help_text = FIELD_HELP[db_field.name]
    return formfield


def formfield_for_dbfield(self, db_field, request, **kwargs):
    return _with_help(_orig_formfield(self, db_field, request, **kwargs), db_field)


def changelist_view(self, request, extra_context=None):
    """Başlık: 'Değiştirmek için X seçin' yerine sade 'Xler'."""
    return _orig_changelist(self, request, {"title": capfirst(self.model._meta.verbose_name_plural), **(extra_context or {})})


def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
    name = self.model._meta.verbose_name
    title = f"{capfirst(name)} düzenle" if object_id else f"Yeni {name}"
    return _orig_changeform(self, request, object_id, form_url, {"title": title, **(extra_context or {})})


admin.ModelAdmin.formfield_for_dbfield = formfield_for_dbfield
admin.options.InlineModelAdmin.formfield_for_dbfield = formfield_for_dbfield
admin.ModelAdmin.changelist_view = changelist_view
admin.ModelAdmin.changeform_view = changeform_view
