from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from . import services
from .models import (Account, ChannelCostProfile, Invoice, InvoiceLine, LedgerEntry, MarketplaceSettlement, Payment,
                     ProductCostExtra)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "iban", "currency", "channel", "active")
    list_filter = ("kind", "active")


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    fields = ("product", "description", "quantity", "unit_price", "vat_rate", "net_amount", "vat_amount")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("__str__", "issue_date", "direction", "kind", "doc_type", "buyer_title", "total", "status", "open_link")
    list_filter = ("direction", "kind", "doc_type", "status")
    search_fields = ("number", "buyer_title", "buyer_vkn", "sales_order__number")
    readonly_fields = [f.name for f in Invoice._meta.fields if f.name not in ("buyer_email", "buyer_alias", "due_date")]
    inlines = [InvoiceLineInline]

    def has_add_permission(self, request):
        return False

    @admin.display(description="")
    def open_link(self, obj):
        return format_html('<a href="{}">Aç</a>', reverse("accounting:invoice", args=[obj.pk]))


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("date", "direction", "partner", "amount", "method", "account", "invoice", "reference")
    list_filter = ("direction", "method", "account")
    search_fields = ("partner__name", "reference")
    autocomplete_fields = ["partner"]
    raw_id_fields = ["invoice"]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in Payment._meta.fields] if obj else []

    def save_model(self, request, obj, form, change):
        if change:
            return
        try:
            pay = services.register_payment(obj.partner, obj.account, obj.amount, obj.direction, obj.date, obj.method,
                                            obj.invoice, obj.reference, obj.fee, request.user)
            obj.pk = pay.pk
        except ValidationError as exc:
            self.message_user(request, " ".join(exc.messages), messages.ERROR)
            raise


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "partner", "doc_type", "description", "debit", "credit", "due_date")
    list_filter = ("doc_type",)
    search_fields = ("partner__name", "description")
    readonly_fields = [f.name for f in LedgerEntry._meta.fields]

    def has_add_permission(self, request):
        return request.user.is_superuser  # yalnız açılış bakiyesi girişi için

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MarketplaceSettlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("__str__", "gross_sales", "expected_net", "bank_received", "difference", "status")
    list_filter = ("channel", "status")
    readonly_fields = ("status", "expected_net", "difference")
    actions = ["fill_estimate", "do_reconcile"]

    @admin.action(description="Sipariş verisinden tahmini doldur (satış, komisyon, kargo)")
    def fill_estimate(self, request, queryset):
        for s in queryset:
            e = services.settlement_estimate(s.channel, s.period_start, s.period_end)
            s.gross_sales, s.commission, s.shipping, s.service_fees = e["gross_sales"], e["commission"], e["shipping"], e["service_fees"]
            s.save()
            self.message_user(request, f"{s}: {e['orders']} sipariş üzerinden dolduruldu.")

    @admin.action(description="Bankaya yatanla karşılaştır (mutabakat)")
    def do_reconcile(self, request, queryset):
        for s in queryset:
            services.reconcile(s)
            self.message_user(request, f"{s}: fark {s.difference} → {s.get_status_display()}",
                              messages.SUCCESS if s.status == "matched" else messages.WARNING)


admin.site.register(ChannelCostProfile, list_display=["channel", "commission_pct", "shipping_cost_per_order", "ad_cost_pct"])
admin.site.register(ProductCostExtra, list_display=["product", "packaging_cost", "storage_cost", "other_cost"],
                    autocomplete_fields=["product"])
