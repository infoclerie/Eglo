"""Sol menüde 'Satış kanalları' grubu: kurulu her pazaryeri / e-ticaret bağlantısı için kanal paneli bağlantısı."""
from django.urls import reverse

from .models import IntegrationAccount


def channel_menu(request):
    if not request.user.has_perm("integrations.view_integrationaccount"):
        return []
    items = []
    for acc in IntegrationAccount.objects.filter(active=True).order_by("name"):
        p = acc.provider_obj
        if p and p.category in ("marketplace", "ecommerce"):
            items.append({"label": acc.name, "url": reverse("integrations:channel", args=[acc.pk]), "icon": "cart"})
    if not items:
        return []
    return [{"code": "channels", "name": "Satış kanalları", "icon": "cart", "color": "#f27a1a", "items": items}]
