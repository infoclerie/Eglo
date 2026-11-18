from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "group", "phone", "city", "credit_limit", "sales_rep", "active")
    list_filter = ("kind", "group", "active", "e_invoice_user", "city")
    search_fields = ("code", "name", "tax_number", "phone", "email")
    readonly_fields = ("code",)
    fieldsets = [
        ("Kimlik", {"fields": ["code", "name", "kind", "group", "active", "sales_rep"]}),
        ("İletişim", {"fields": ["contact_person", "phone", "email", "address", "shipping_address", "city", "district"]}),
        ("Vergi", {"fields": ["tax_office", "tax_number", "e_invoice_user"]}),
        ("Ticari koşullar", {"fields": ["payment_term_days", "credit_limit", "discount_pct", "default_channel", "iban", "lead_time_days"]}),
        ("İletişim izinleri (KVKK / İYS)", {"fields": ["consent_sms", "consent_email", "consent_date"]}),
        ("Not", {"fields": ["note"]}),
    ]
