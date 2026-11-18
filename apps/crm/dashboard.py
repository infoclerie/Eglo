from django.urls import reverse

from . import services


def widgets(request):
    n = services.due_activities(request.user).count()
    return [{"title": "Bugün yapılacak müşteri takibi", "value": n, "url": reverse("crm:activities"), "level": "warning" if n else "ok"}]
