"""
Rol tanımları (müşteri dokümanı §12). Her rol bir Django Group'tur.
Biçim: rol adı -> {app_label: "all" | "view" | [izin kodları]}
Yeni modül eklendiğinde ilgili rollere burada izin ver ve `python manage.py setup_roles` çalıştır.
"""
ROLES = {
    "Şirket yöneticisi": {"*": "all", "core": "all"},
    "Depo müdürü": {"catalog": "all", "inventory": "all", "shipping": "all", "purchase": "view", "sales": "view", "partners": "view", "core": ["decide_approval", "view_approvalrequest"]},
    "Depo personeli": {"catalog": "view", "inventory": [
        "view_quant", "view_location", "view_lot", "view_pallet", "add_pallet", "change_pallet",
        "view_stockmove", "add_stockmove", "add_stockcount", "change_stockcount", "view_stockcount",
        "add_stockcountline", "change_stockcountline", "view_stockcountline"],
        "shipping": ["view_shipment", "change_shipment", "view_shipmentline"], "purchase": ["view_purchaseorder"]},
    "Satın alma": {"catalog": "view", "inventory": "view", "partners": "all", "purchase": "all"},
    "Satış ekibi": {"catalog": "view", "inventory": ["view_quant"], "partners": "all", "sales": "all"},
    "E-ticaret ekibi": {"catalog": "view", "inventory": ["view_quant"], "partners": "view", "sales": "all", "shipping": "view"},
    "Finans": {"catalog": "view", "partners": "all", "sales": "view", "purchase": "view", "accounting": "all", "integrations": "view"},
    "Muhasebe": {"catalog": "view", "partners": "view", "sales": "view", "purchase": "view", "accounting": "all", "integrations": "all"},
    "Sevkiyat personeli": {"catalog": "view", "inventory": ["view_quant", "view_location", "view_stockmove"], "sales": ["view_salesorder"], "shipping": ["view_shipment", "change_shipment", "view_shipmentline", "view_returnrequest", "change_returnrequest", "add_returnrequest", "view_returnline", "add_returnline", "change_returnline"]},
    "Raporlama kullanıcısı": {"*": "view"},
}
