from django.contrib import admin

from .models import BillOfMaterials, BomLine, ProductionOrder


class BomLineInline(admin.TabularInline):
    model = BomLine
    extra = 3
    autocomplete_fields = ["component"]


@admin.register(BillOfMaterials)
class BomAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "batch_size", "active")
    list_filter = ("active",)
    search_fields = ("code", "product__name", "product__sku")
    autocomplete_fields = ["product"]
    inlines = [BomLineInline]


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "product", "kind", "planned_qty", "produced_qty", "status", "planned_date")
    list_filter = ("status", "kind")
    search_fields = ("number", "product__name", "lot_no")
    readonly_fields = [f.name for f in ProductionOrder._meta.fields if f.name not in ("note", "planned_date")]

    def has_add_permission(self, request):
        return False  # üretim emri ekranından açılır (stok akışı servis üzerinden)
