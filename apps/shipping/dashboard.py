from django.urls import reverse

from .models import ReturnRequest, Shipment


def widgets(request):
    waiting = Shipment.objects.filter(status__in=["waiting", "picking", "picked", "packed"]).count()
    returns = ReturnRequest.objects.exclude(status__in=["completed", "rejected"]).count()
    return [
        {"title": "Hazırlanacak sevkiyat", "value": waiting, "url": reverse("shipping:queue"),
         "level": "warning" if waiting else "ok"},
        {"title": "Açık iade", "value": returns, "url": reverse("admin:shipping_returnrequest_changelist"),
         "level": "warning" if returns else "ok"},
    ]
