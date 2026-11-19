from apps.core.formats import tl
from django.urls import reverse

from . import services
from .models import Invoice


def widgets(request):
    overdue = services.overdue_receivables()
    errors = Invoice.objects.filter(status__in=["error", "on_hold"]).count()
    total = sum((r["open"] for r in overdue), 0)
    return [
        {"title": "Vadesi geçmiş alacak", "value": tl(total), "url": reverse("accounting:balances"),
         "level": "danger" if overdue else "ok"},
        {"title": "Hatalı / onay bekleyen fatura", "value": errors, "url": reverse("accounting:invoices") + "?tab=problem",
         "level": "danger" if errors else "ok"},
    ]
