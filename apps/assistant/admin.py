from django.contrib import admin

from .models import AssistantMessage


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "role", "short", "tokens_in", "tokens_out", "provider")
    list_filter = ("role", "provider", "user")
    search_fields = ("content",)
    readonly_fields = [f.name for f in AssistantMessage._meta.fields]

    @admin.display(description="Metin")
    def short(self, obj):
        return obj.content[:90]

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.has_perm("assistant.view_all_usage") else qs.filter(user=request.user)
