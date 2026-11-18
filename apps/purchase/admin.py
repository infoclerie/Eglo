from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from . import services
from .models import PurchaseOrder, PurchaseOrderLine, PurchaseRequest, ReceiptDiscrepancy, SupplierQuote


class LineInline(admin.TabularInline):
    model = PurchaseOrderLine
    fields = ("product", "quantity", "unit_price", "vat_rate", "received_quantity")
    readonly_fields = ("received_quantity",)
    autocomplete_fields = ["product"]
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "status", "order_date", "expected_date", "total", "late", "receive_link")
    list_filter = ("status", "warehouse")
    search_fields = ("number", "supplier__name")
    autocomplete_fields = ["supplier"]
    readonly_fields = ("number", "status")
    inlines = [LineInline]
    actions = ["submit", "mark_sent", "close"]

    @admin.display(description="Gecikme", boolean=True)
    def late(self, obj):
        return bool(obj.is_late)

    @admin.display(description="Mal kabul")
    def receive_link(self, obj):
        if obj.status in PurchaseOrder.OPEN:
            return format_html('<a href="{}">Mal kabul</a>', reverse("purchase:receive", args=[obj.pk]))
        return "-"

    def save_model(self, request, obj, form, change):
        if not change:
            from apps.core.models import Sequence
            obj.number = Sequence.next("purchase.order", "SAS-")
        super().save_model(request, obj, form, change)

    def _run(self, request, queryset, fn, text):
        for po in queryset:
            try:
                fn(po, request.user)
                self.message_user(request, f"{po.number}: {text}", messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request, f"{po.number}: {' '.join(exc.messages)}", messages.ERROR)

    @admin.action(description="Yönetici onayına gönder")
    def submit(self, request, queryset):
        self._run(request, queryset, services.submit, "onaya gönderildi")

    @admin.action(description="Tedarikçiye iletildi olarak işaretle")
    def mark_sent(self, request, queryset):
        self._run(request, queryset, services.mark_sent, "iletildi")

    @admin.action(description="Kapat (eksik/fazla teslim tutanağı oluştur)")
    def close(self, request, queryset):
        self._run(request, queryset, services.close, "kapatıldı")


class QuoteInline(admin.TabularInline):
    model = SupplierQuote
    fields = ("supplier", "product", "unit_price", "lead_time_days", "payment_term_days", "min_order_qty", "valid_until")
    autocomplete_fields = ["supplier", "product"]
    extra = 0


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "source", "status", "needed_by", "reason", "created_at")
    list_filter = ("status", "source")
    autocomplete_fields = ["product"]
    inlines = [QuoteInline]


@admin.register(SupplierQuote)
class SupplierQuoteAdmin(admin.ModelAdmin):
    list_display = ("product", "supplier", "unit_price", "lead_time_days", "payment_term_days", "valid_until")
    list_filter = ("supplier",)
    search_fields = ("product__sku", "supplier__name")
    ordering = ("product", "unit_price", "lead_time_days")


@admin.register(ReceiptDiscrepancy)
class ReceiptDiscrepancyAdmin(admin.ModelAdmin):
    list_display = ("line", "kind", "ordered", "received", "at", "note")
    list_filter = ("kind",)
