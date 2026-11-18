from django.urls import reverse

from .models import IntegrationJob


def widgets(request):
    failed = IntegrationJob.objects.filter(status="failed").count()
    return [{"title": "Başarısız entegrasyon işi", "value": failed, "url": reverse("integrations:jobs") + "?status=failed",
             "level": "danger" if failed else "ok"}]
