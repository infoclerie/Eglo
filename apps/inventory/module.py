MANIFEST = {
    "code": "inventory",
    "name": "Depo ve Stok (WMS)",
    "version": "0.1.0",
    "depends": ["core", "catalog"],
    "urls": "apps.inventory.urls",
    "icon": "warehouse",
    "color": "#0f9d8a",
    "menu": [
        ("Stok Durumu", "inventory:summary", "warehouse"),
        ("Barkod Sorgu", "inventory:scan", "scan"),
        ("Mal Kabul", "inventory:receive", "inbox"),
        ("Transfer", "inventory:transfer", "swap"),
        ("Sayımlar", "admin:inventory_stockcount_changelist", "check"),
    ],
}
