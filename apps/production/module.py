MANIFEST = {
    "code": "production",
    "name": "Üretim ve Fason",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "partners"],
    "urls": "apps.production.urls",
    "icon": "box",
    "color": "#7c3aed",
    "menu": [("Üretim emirleri", "production:list", "box"), ("Yeni üretim emri", "production:new", "plus"),
             ("Reçeteler", "admin:production_billofmaterials_changelist", "settings")],
    "reset_data": [{'label': 'Üretim emirleri', 'desc': 'Üretim emirleri (reçeteler kalır).', 'models': ['production.ProductionOrder'], 'sequences': ['production.']}],
}
