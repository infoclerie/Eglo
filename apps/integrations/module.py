MANIFEST = {
    "code": "integrations",
    "name": "Entegrasyonlar",
    "version": "0.1.0",
    "depends": ["core", "accounting"],
    "urls": "apps.integrations.urls",
    "icon": "plug",
    "color": "#0b6bcb",
    "menu": [("Bağlantılar", "integrations:home", "plug"), ("İş kuyruğu ve hatalar", "integrations:jobs", "alert")],
    "reset_data": [{'label': 'Entegrasyon işleri ve kayıtları', 'desc': 'İş kuyruğu, loglar ve pazaryeri sipariş eşleşmeleri (bağlantı ayarları ve ürün eşleştirmeleri kalır).', 'models': ['integrations.ExternalOrder', 'integrations.SyncLog', 'integrations.IntegrationJob']}],
}
