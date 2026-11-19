MANIFEST = {
    "code": "shipping",
    "name": "Sevkiyat ve İade",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "sales"],
    "urls": "apps.shipping.urls",
    "icon": "truck",
    "color": "#7a5af8",
    "menu": [("Toplama / Sevkiyat", "shipping:queue", "truck"), ("İadeler", "admin:shipping_returnrequest_changelist", "return")],
    "reset_data": [{'label': 'Sevkiyatlar ve iadeler', 'desc': 'Toplama, paketleme, sevk ve iade kayıtları.', 'models': ['shipping.ReturnLine', 'shipping.ReturnRequest', 'shipping.ShipmentLine', 'shipping.Shipment'], 'sequences': ['shipping.']}],
}
