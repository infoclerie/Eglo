MANIFEST = {
    "code": "portal",
    "name": "Bayi Portalı",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "partners", "sales", "accounting"],
    "urls": "apps.portal.urls",
    "icon": "users",
    "color": "#0f766e",
    "menu": [("Bayi kullanıcıları", "admin:portal_portalaccess_changelist", "users")],
}
