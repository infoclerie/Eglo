MANIFEST = {
    "code": "crm",
    "name": "CRM",
    "version": "0.1.0",
    "depends": ["core", "partners", "sales", "integrations", "notifications"],
    "urls": "apps.crm.urls",
    "icon": "users",
    "color": "#be185d",
    "menu": [("Satış fırsatları", "crm:board", "chart"), ("Takiplerim", "crm:activities", "check"), ("Müşteri segmentleri", "crm:segments", "users"), ("Kampanyalar (e-posta / SMS)", "crm:campaigns", "inbox")],
}
