"""
Rol tanımları (müşteri dokümanı §12). Her rol bir Django Group'tur.
Biçim: rol adı -> {app_label: "all" | "view" | [izin kodları]}
Yeni modül eklendiğinde ilgili rollere burada izin ver ve `python manage.py setup_roles` çalıştır.
"""
ROLES = {
    "Şirket yöneticisi": {"*": "all", "core": "all"},
    "Depo müdürü": {"catalog": "all", "inventory": "all", "core": ["decide_approval", "view_approvalrequest"]},
    "Depo personeli": {"catalog": "view", "inventory": [
        "view_quant", "view_location", "view_lot", "view_pallet", "add_pallet", "change_pallet",
        "view_stockmove", "add_stockmove", "add_stockcount", "change_stockcount", "view_stockcount",
        "add_stockcountline", "change_stockcountline", "view_stockcountline"]},
    "Satın alma": {"catalog": "view", "inventory": "view"},
    "Satış ekibi": {"catalog": "view", "inventory": ["view_quant"]},
    "E-ticaret ekibi": {"catalog": "view", "inventory": ["view_quant"]},
    "Finans": {"catalog": "view"},
    "Muhasebe": {"catalog": "view"},
    "Sevkiyat personeli": {"catalog": "view", "inventory": ["view_quant", "view_location", "view_stockmove"]},
    "Raporlama kullanıcısı": {"*": "view"},
}
