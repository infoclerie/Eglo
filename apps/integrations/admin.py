from django.contrib import admin

from .models import IntegrationAccount, IntegrationJob, SyncLog


@admin.register(IntegrationAccount)
class IntegrationAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "environment", "active", "last_test_ok", "last_test_at")
    readonly_fields = ("provider", "secret", "last_test_at", "last_test_ok", "last_message")


@admin.register(IntegrationJob)
class IntegrationJobAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "kind", "ref", "status", "attempts", "next_run_at")
    list_filter = ("status", "kind", "account")
    search_fields = ("ref", "idempotency_key")


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("at", "account", "action", "ok", "message")
    list_filter = ("ok", "action", "account")
    readonly_fields = [f.name for f in SyncLog._meta.fields]
