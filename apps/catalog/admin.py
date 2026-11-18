from django.contrib import admin

from .models import Brand, Category, KitComponent, Product, ProductPrice, SalesChannel


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0


class KitComponentInline(admin.TabularInline):
    model = KitComponent
    fk_name = "kit"
    extra = 0
    autocomplete_fields = ["component"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "barcode", "name", "brand", "group", "kind", "list_price", "min_stock", "active")
    list_filter = ("active", "kind", "group", "brand", "category", "track_lot")
    search_fields = ("sku", "barcode", "case_barcode", "name")
    inlines = [ProductPriceInline, KitComponentInline]
    fieldsets = [
        ("Kimlik", {"fields": ["sku", "barcode", "name", "brand", "category", "group", "kind", "active", "description", "image_url"]}),
        ("Birim ve ambalaj", {"fields": ["unit", "volume", "weight_kg", "units_per_case", "case_barcode", "cases_per_pallet"]}),
        ("Fiyat ve vergi", {"fields": ["cost", "list_price", "vat_rate"]}),
        ("Stok parametreleri", {"fields": ["min_stock", "max_stock", "safety_stock", "lead_time_days"]}),
        ("LOT / SKT", {"fields": ["track_lot", "shelf_life_days", "storage_condition"]}),
    ]


admin.site.register(Brand, search_fields=["name"])
admin.site.register(Category, search_fields=["name"], list_display=["__str__"])
admin.site.register(SalesChannel, list_display=["code", "name", "active"])
