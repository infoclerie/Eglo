MANIFEST = {
    "code": "notifications",
    "name": "Bildirimler",
    "version": "0.1.0",
    "depends": ["core"],
    "urls": "apps.notifications.urls",
    "icon": "alert",
    "color": "#c2410c",
    "menu": [("Bildirimlerim", "notifications:list", "alert"), ("Bildirim merkezi", "notifications:center", "settings")],
    "reset_data": [{'label': 'Bildirimler', 'desc': 'Zildeki bildirimler (bildirim merkezi ayarları ve şablonlar kalır).', 'models': ['notifications.Notification']}],
}
