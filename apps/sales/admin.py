from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from . import services
from .models import Campaign, OrderStatusLog, SalesOrder, SalesOrderLine


class LineInline(admin.TabularInline):
    model = SalesOrderLine
    fields = ("product", "quantity", "unit_price", "vat_rate", "discount", "order_discount_share", "vat_amount")
    readonly_fields = ("discount", "order_discount_share", "vat_amount")
    autocomplete_fields = ["product"]
    extra = 0

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.status in SalesOrder.EDITABLE

    has_add_permission = has_delete_permission = lambda self, request, obj=None: obj is None or obj.status in SalesOrder.EDITABLE


class StatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    fields = ("at", "status", "user", "note")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "order_date", "channel", "external_ref", "display_customer", "status", "grand_total")
    list_filter = ("status", "channel", "payment_method")
    search_fields = ("number", "external_ref", "customer_name", "customer__name", "phone")
    autocomplete_fields = ["customer"]
    readonly_fields = ("number", "status", "status_changed_at", "subtotal", "discount_total", "vat_total",
                       "grand_total", "applied_campaigns", "credit_approved")
    inlines = [LineInline, StatusLogInline]
    actions = ["confirm_orders", "cancel_orders", "credit_override"]
    fieldsets = [
        ("Sipariş", {"fields": ["number", "order_date", "channel", "external_ref", "warehouse", "status", "status_changed_at"]}),
        ("Müşteri", {"fields": ["customer", "customer_name", "phone", "email", "tax_number", "shipping_address", "billing_address"]}),
        ("Ödeme ve tutarlar", {"fields": ["payment_method", "coupon_code", "shipping_fee", "subtotal", "discount_total",
                                         "vat_total", "grand_total", "applied_campaigns", "credit_approved"]}),
        ("Not", {"fields": ["note"]}),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            from apps.core.models import Sequence
            obj.number = Sequence.next("sales.order", "SIP-")
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if form.instance.status in SalesOrder.EDITABLE:
            services.compute_totals(form.instance)

    def _run(self, request, queryset, fn, ok_text):
        for o in queryset:
            try:
                res = fn(o, request.user)
                self.message_user(request, f"{o}: {ok_text if not hasattr(res, 'action') else 'onaya gönderildi'}",
                                  messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request, f"{o}: {' '.join(exc.messages)}", messages.ERROR)

    @admin.action(description="Onayla (stok rezerve et, toplamaya gönder)")
    def confirm_orders(self, request, queryset):
        self._run(request, queryset, services.confirm, "onaylandı")

    @admin.action(description="İptal et / iptal onayı iste")
    def cancel_orders(self, request, queryset):
        self._run(request, queryset, services.request_cancel, "iptal edildi")

    @admin.action(description="Kredi limiti aşımı için onay iste")
    def credit_override(self, request, queryset):
        self._run(request, queryset, services.request_credit_override, "")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "starts_at", "ends_at", "used_count", "max_uses", "active")
    list_filter = ("kind", "active", "channels")
    filter_horizontal = ("channels", "products")
    search_fields = ("name", "coupon_code")
