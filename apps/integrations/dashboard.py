from django.urls import reverse

from .models import IntegrationJob


def widgets(request):
    from django.utils import timezone

    from .models import ExternalOrder, IntegrationAccount
    failed = IntegrationJob.objects.filter(status="failed").count()
    out = []
    today = timezone.localdate()
    for acc in IntegrationAccount.objects.filter(active=True).order_by("name"):
        p = acc.provider_obj
        if not p or p.category not in ("marketplace", "ecommerce"):
            continue
        last = acc.jobs.exclude(status="pending").order_by("-created_at").first()
        n = ExternalOrder.objects.filter(account=acc, created_at__date=today).count()
        broken = last is not None and last.status == "failed"
        out.append({"title": f"{acc.name} · bugün sipariş" + (" (bağlantı hatası!)" if broken else ""), "value": n,
                    "url": reverse("integrations:channel", args=[acc.pk]), "level": "danger" if broken else "ok", "key": f"integrations.kanal-{acc.pk}"})
    out.append({"title": "Başarısız entegrasyon işi", "value": failed, "url": reverse("integrations:jobs") + "?status=failed",
                "level": "danger" if failed else "ok"})
    return out
