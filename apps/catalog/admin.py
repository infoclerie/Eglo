from django.contrib import admin

from django.urls import reverse
from django.utils.html import format_html

from .models import Brand, Category, KitComponent, Product, ProductImage, ProductPrice, SalesChannel


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("preview", "is_main", "note", "created_at")
    readonly_fields = ("preview", "is_main", "created_at")
    can_delete = False
    verbose_name_plural = "Fotoğraflar (yükleme ve düzenleme için ürünün 'Fotoğraflar' sayfasını kullanın)"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Fotoğraf")
    def preview(self, obj):
        return format_html('<a href="{}" target="_blank"><img src="{}" style="width:72px;height:72px;object-fit:cover;border-radius:8px"></a>',
                           obj.image.url, (obj.thumb or obj.image).url)


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
    list_display = ("photo", "sku", "barcode", "name", "brand", "group", "kind", "list_price", "min_stock", "active")
    list_display_links = ("sku", "name")
    list_filter = ("active", "kind", "group", "brand", "category", "track_lot")
    search_fields = ("sku", "barcode", "case_barcode", "name")
    inlines = [ProductPriceInline, KitComponentInline, ProductImageInline]
    readonly_fields = ("photos_link",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("images")

    @admin.display(description="")
    def photo(self, obj):
        m = obj.main_image
        if m is None:
            return format_html('<span style="display:inline-block;width:40px;height:40px;border-radius:8px;background:#f3f4f6"></span>')
        return format_html('<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:8px">', (m.thumb or m.image).url)

    @admin.display(description="Fotoğraflar")
    def photos_link(self, obj):
        if not obj.pk:
            return "Ürünü kaydettikten sonra fotoğraf ekleyebilirsiniz."
        return format_html('<a class="button" href="{}">📷 Fotoğraf ekle / yönet ({})</a>', reverse("catalog:photos", args=[obj.pk]), obj.images.count())
    fieldsets = [
        ("Kimlik", {"fields": ["sku", "barcode", "name", "brand", "category", "group", "kind", "active", "description", "photos_link"]}),
        ("Birim ve ambalaj", {"fields": ["unit", "volume", "weight_kg", "units_per_case", "case_barcode", "cases_per_pallet"]}),
        ("Fiyat ve vergi", {"fields": ["cost", "list_price", "vat_rate"]}),
        ("Stok parametreleri", {"fields": ["min_stock", "max_stock", "safety_stock", "lead_time_days"]}),
        ("LOT / SKT", {"fields": ["track_lot", "shelf_life_days", "storage_condition"]}),
    ]


admin.site.register(Brand, search_fields=["name"])
admin.site.register(Category, search_fields=["name"], list_display=["__str__"])
admin.site.register(SalesChannel, list_display=["code", "name", "active"])
