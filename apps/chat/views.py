import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import services


@login_required
def poll(request):
    """Sinyal + sohbet listesi + (açık sohbet varsa) yeni mesajlar."""
    services.touch(request.user)
    data = {"conversations": services.conversations(request.user)}
    data["unread"] = sum(c["unread"] for c in data["conversations"])
    conv_id = request.GET.get("conv")
    if conv_id:
        try:
            conv = services.get_conv(request.user, conv_id)
            data["messages"] = services.messages_after(request.user, conv, int(request.GET.get("after") or 0))
        except PermissionDenied:
            data["messages"] = []
    return JsonResponse(data)


@login_required
def people(request):
    """Sohbet başlatılabilecek kişiler ve çevrimiçi durumu (bayi kullanıcısı yalnız desteği görür)."""
    if services.is_portal(request.user):
        return JsonResponse({"people": [], "support": True})
    online = services.online_ids()
    return JsonResponse({"support": False, "people": [
        {"id": u.pk, "name": u.get_full_name() or u.username, "online": u.pk in online}
        for u in services.staff_users().exclude(pk=request.user.pk)]})


@login_required
@require_POST
def start(request):
    data = json.loads(request.body or "{}")
    if data.get("support"):
        if not services.is_portal(request.user):
            raise PermissionDenied
        conv = services.support_for(request.user)
    else:
        other = get_user_model().objects.get(pk=data.get("user"), is_active=True)
        conv = services.direct_with(request.user, other)
    return JsonResponse({"id": conv.pk})


@login_required
@require_POST
def send(request):
    data = json.loads(request.body or "{}")
    conv = services.get_conv(request.user, data.get("conv"))
    m = services.send(request.user, conv, data.get("body"))
    return JsonResponse({"ok": bool(m)})
