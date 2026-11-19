MANIFEST = {
    "code": "purchase",
    "name": "Satın Alma",
    "version": "0.1.0",
    "depends": ["core", "catalog", "inventory", "partners"],
    "urls": "apps.purchase.urls",
    "icon": "bag",
    "color": "#b26a00",
    "menu": [("Satın Alma Siparişleri", "admin:purchase_purchaseorder_changelist", "bag"), ("Talepler ve Teklifler", "admin:purchase_purchaserequest_changelist", "bag")],
    "reset_data": [{'label': 'Satın alma', 'desc': 'Talepler, teklifler, satın alma siparişleri ve tutanaklar.', 'models': ['purchase.ReceiptDiscrepancy', 'purchase.PurchaseOrderLine', 'purchase.PurchaseOrder', 'purchase.SupplierQuote', 'purchase.PurchaseRequest'], 'sequences': ['purchase.']}],
}
