from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from . import services
from .models import ReturnLine, ReturnRequest, Shipment, ShipmentLine


class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    fields = ("location", "product", "lot", "quantity", "picked_quantity")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "status", "method", "priority", "carrier", "tracking_no", "shipped_at")
    list_filter = ("status", "carrier", "method")
    search_fields = ("number", "order__number", "order__external_ref", "tracking_no")
    readonly_fields = ("number", "order", "status", "expected_weight_kg", "weight_kg", "package_count", "shipped_at",
                       "delivered_at", "picker")
    inlines = [ShipmentLineInline]

    def has_add_permission(self, request):
        return False


class ReturnLineInline(admin.TabularInline):
    model = ReturnLine
    fields = ("product", "quantity", "lot", "condition")
    readonly_fields = ("lot",)
    autocomplete_fields = ["product"]
    extra = 0


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "reason", "status", "return_code", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("number", "order__number", "return_code")
    readonly_fields = ("number", "status", "return_code")
    autocomplete_fields = ["order"]
    inlines = [ReturnLineInline]
    actions = ["receive", "inspect"]

    def save_model(self, request, obj, form, change):
        if not change:
            from apps.core.models import Sequence
            obj.number = Sequence.next("shipping.return", "IADE-")
        super().save_model(request, obj, form, change)

    @admin.action(description="İade ürünleri depoya ulaştı (iade kontrol alanına al)")
    def receive(self, request, queryset):
        for rr in queryset:
            try:
                services.receive_return(rr, request.user)
                self.message_user(request, f"{rr} teslim alındı.", messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request, f"{rr}: {' '.join(exc.messages)}", messages.ERROR)

    @admin.action(description="Kontrol tamam → yönetici onayına gönder (satırlarda ürün durumu seçili olmalı)")
    def inspect(self, request, queryset):
        for rr in queryset:
            try:
                services.inspect_return(rr, {l.pk: l.condition for l in rr.lines.all()}, request.user)
                self.message_user(request, f"{rr} onaya gönderildi.", messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request, f"{rr}: {' '.join(exc.messages)}", messages.ERROR)
