MANIFEST = {
    "code": "partners",
    "name": "Cari Kartlar",
    "version": "0.1.0",
    "depends": ["core", "catalog"],
    "icon": "users",
    "color": "#2563c9",
    "menu": [("Cariler", "admin:partners_partner_changelist", "users")],
    "reset_master": [{'label': 'Cariler (müşteri, bayi, tedarikçi)', 'desc': 'Tüm cari kartlar. Bayi portal erişimleri de kalkar (kullanıcı hesapları kalır).', 'models': ['partners.Partner'], 'sequences': ['partners.']}],
}
