MANIFEST = {
    "code": "sales",
    "name": "Sipariş Yönetimi",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "partners"],
    "urls": "apps.sales.urls",
    "icon": "cart",
    "color": "#d9485f",
    "menu": [("Sipariş Havuzu", "sales:pool", "cart"), ("Yeni Sipariş", "admin:sales_salesorder_add", "cart"), ("Kampanyalar", "admin:sales_campaign_changelist", "tag")],
    "reset_data": [{'label': 'Satış siparişleri', 'desc': 'Tüm siparişler ve durum geçmişi (kampanya tanımları kalır).', 'models': ['sales.OrderStatusLog', 'sales.SalesOrderLine', 'sales.SalesOrder'], 'sequences': ['sales.']}],
}
