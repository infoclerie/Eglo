from django.urls import reverse

from .models import PurchaseOrder, PurchaseRequest


def widgets(request):
    late = sum(1 for p in PurchaseOrder.objects.filter(status__in=PurchaseOrder.OPEN) if p.is_late)
    open_req = PurchaseRequest.objects.filter(status="open").count()
    return [
        {"title": "Termini geçen satın alma", "value": late, "url": reverse("admin:purchase_purchaseorder_changelist"),
         "level": "danger" if late else "ok"},
        {"title": "Açık satın alma talebi", "value": open_req, "url": reverse("admin:purchase_purchaserequest_changelist"),
         "level": "warning" if open_req else "ok"},
    ]
