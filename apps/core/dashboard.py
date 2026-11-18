from django.urls import reverse

from .models import ApprovalRequest


def widgets(request):
    pending = ApprovalRequest.objects.filter(status="pending").count()
    return [{
        "title": "Onay bekleyen işlem", "value": pending,
        "url": reverse("admin:core_approvalrequest_changelist") + "?status__exact=pending",
        "level": "warning" if pending else "ok",
    }]
