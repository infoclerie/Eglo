MANIFEST = {
    "code": "catalog",
    "name": "Ürün Kartları",
    "version": "0.1.0",
    "depends": ["core"],
    "urls": "apps.catalog.urls",
    "icon": "tag",
    "color": "#e07a2e",
    "menu": [("Ürünler", "admin:catalog_product_changelist", "tag"), ("Markalar ve Kategoriler", "admin:catalog_category_changelist", "tag")],
}
