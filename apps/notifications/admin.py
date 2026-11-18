from django.contrib import admin

from .models import ContactInfo, NotificationRule


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ("event", "group", "in_app", "email", "sms", "active")
    list_editable = ("in_app", "email", "sms", "active")
    list_filter = ("event", "group")

    def has_add_permission(self, request):
        return request.user.is_superuser


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "mobile")
    autocomplete_fields = ["user"]
