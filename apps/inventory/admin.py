from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from . import services
from .models import Location, Lot, Pallet, Quant, Reservation, StockCount, StockCountLine, StockMove, Warehouse


class ReadOnlyAdmin(admin.ModelAdmin):
    """Stok tabloları sadece servisler üzerinden değişir; panelde salt okunur."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "external", "active")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("code", "warehouse", "kind", "is_sellable", "can_pick", "active")
    list_filter = ("warehouse", "kind", "is_sellable", "active")
    search_fields = ("code", "barcode", "name")


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("lot_no", "product", "production_date", "expiry_date", "days_left", "status")
    list_filter = ("expiry_date",)
    search_fields = ("lot_no", "product__sku", "product__name")
    autocomplete_fields = ["product"]

    @admin.display(description="Kalan gün")
    def days_left(self, obj):
        return obj.days_to_expiry()

    @admin.display(description="SKT durumu")
    def status(self, obj):
        return services.EXPIRY_LABELS.get(services.expiry_status(obj), "-")


class PalletQuantInline(admin.TabularInline):
    model = Quant
    fields = ("product", "lot", "location", "quantity", "reserved_quantity")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pallet)
class PalletAdmin(admin.ModelAdmin):
    list_display = ("code", "location", "max_cases", "active")
    search_fields = ("code",)
    inlines = [PalletQuantInline]


@admin.register(Quant)
class QuantAdmin(ReadOnlyAdmin):
    list_display = ("product", "location", "lot", "pallet", "quantity", "reserved_quantity")
    list_filter = ("location__warehouse", "location__kind")
    search_fields = ("product__sku", "product__name", "lot__lot_no", "location__code")


@admin.register(StockMove)
class StockMoveAdmin(ReadOnlyAdmin):
    list_display = ("date", "move_type", "product", "quantity", "source", "destination", "lot", "reference", "user")
    list_filter = ("move_type", "date")
    search_fields = ("product__sku", "reference", "lot__lot_no")
    date_hierarchy = "date"


@admin.register(Reservation)
class ReservationAdmin(ReadOnlyAdmin):
    list_display = ("reference", "product", "quant", "quantity", "created_at")
    search_fields = ("reference", "product__sku")


class CountLineInline(admin.TabularInline):
    model = StockCountLine
    fields = ("product", "location", "lot", "system_quantity", "counted_quantity", "difference")
    readonly_fields = ("system_quantity", "difference")
    autocomplete_fields = ["product"]
    extra = 0


@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
    list_display = ("number", "warehouse", "kind", "status", "created_at", "created_by")
    list_filter = ("status", "warehouse")
    readonly_fields = ("number", "status")
    inlines = [CountLineInline]
    actions = ["submit"]

    def save_model(self, request, obj, form, change):
        if not change:
            # yeni sayım: satırları sistem stoğundan otomatik doldur
            new = services.start_count(obj.warehouse, obj.kind, user=request.user)
            new.note = obj.note
            new.save()
            obj.pk, obj.number = new.pk, new.number
            obj._state.adding = False
            return
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        return ro + ["warehouse", "kind"] if obj else ro

    @admin.action(description="Sayımı yönetici onayına gönder")
    def submit(self, request, queryset):
        for c in queryset:
            try:
                services.submit_count(c, request.user)
                self.message_user(request, f"{c} onaya gönderildi.", messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request, f"{c}: {exc}", messages.ERROR)
