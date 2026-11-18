MANIFEST = {
    "code": "integrations",
    "name": "Entegrasyonlar",
    "version": "0.1.0",
    "depends": ["core", "accounting"],
    "urls": "apps.integrations.urls",
    "icon": "plug",
    "color": "#0b6bcb",
    "menu": [("Bağlantılar", "integrations:home", "plug"), ("İş kuyruğu ve hatalar", "integrations:jobs", "alert")],
}
