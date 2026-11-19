MANIFEST = {
    "code": "integrations",
    "name": "Entegrasyonlar",
    "version": "0.1.0",
    "depends": ["core", "accounting"],
    "urls": "apps.integrations.urls",
    "icon": "plug",
    "color": "#0b6bcb",
    "menu": [("Bağlantılar", "integrations:home", "plug"), ("İş kuyruğu ve hatalar", "integrations:jobs", "alert")],
    "nav_hook": "apps.integrations.nav.channel_menu",
    "reset_data": [{'label': 'Entegrasyon işleri ve kayıtları', 'desc': 'İş kuyruğu, loglar ve pazaryeri sipariş eşleşmeleri (bağlantı ayarları ve ürün eşleştirmeleri kalır).', 'models': ['integrations.ExternalOrder', 'integrations.SyncLog', 'integrations.IntegrationJob']}],
    "reset_master": [{'label': 'Entegrasyon bağlantıları', 'desc': 'Uyumsoft, Trendyol, Hepsiburada, ikas, e-posta, SMS bağlantıları (şifreleri dahil) ve ürün eşleştirmeleri.', 'models': ['integrations.ChannelListing', 'integrations.IntegrationAccount']}],
}
