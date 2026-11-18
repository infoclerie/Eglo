MANIFEST = {
    "code": "inventory",
    "name": "Depo ve Stok (WMS)",
    "version": "0.1.0",
    "depends": ["core", "catalog"],
    "urls": "apps.inventory.urls",
    "menu": [
        ("Stok Durumu", "inventory:summary"),
        ("Barkod Sorgu", "inventory:scan"),
        ("Mal Kabul", "inventory:receive"),
        ("Transfer", "inventory:transfer"),
    ],
}
