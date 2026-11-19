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
    "reset_data": [{'label': 'Stok miktarları ve hareketleri', 'desc': "Eldeki stok, LOT'lar, hareketler, rezervasyonlar ve sayımlar sıfırlanır (depo, lokasyon, palet tanımları kalır).", 'models': ['inventory.Reservation', 'inventory.StockCountLine', 'inventory.StockCount', 'inventory.Quant', 'inventory.StockMove', 'inventory.Lot'], 'sequences': ['inventory.', 'count']}],
}
