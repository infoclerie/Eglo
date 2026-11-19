MANIFEST = {
    "code": "core",
    "name": "Çekirdek",
    "version": "0.1.0",
    "depends": [],
    "icon": "home",
    "color": "#5b3a6e",
    "menu": [("Ana Panel", "core:dashboard", "home"), ("Onay Bekleyenler", "admin:core_approvalrequest_changelist", "approve")],
    "reset_data": [{'label': 'Onay talepleri ve işlem geçmişi', 'desc': 'Onay bekleyenler ve kim-ne-değiştirdi kayıtları.', 'models': ['core.ApprovalRequest', 'core.AuditLog']}],
}
