import json

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import AssistantMessage

PERM = "assistant.add_assistantmessage"


def _msg(m):
    return {"id": m.id, "role": m.role, "content": m.content, "at": m.created_at.isoformat(),
            "tools": [t["tool"] for t in m.tools_used]}


@login_required
@permission_required(PERM, raise_exception=True)
def index(request):
    if request.method == "POST" and request.POST.get("clear"):
        AssistantMessage.objects.filter(user=request.user).delete()
        return redirect("assistant:index")
    acc = services.account()
    return render(request, "assistant/index.html", {
        "items": AssistantMessage.objects.filter(user=request.user).order_by("-created_at")[:40][::-1],
        "ready": bool(acc and acc.config.get("kvkk_ok")), "acc": acc, "suggestions": services.suggestions(request.user),
        "used": services.used_today(request.user), "limit": int((acc.config.get("daily_limit") if acc else 0) or 50)})


@login_required
@permission_required(PERM, raise_exception=True)
@require_POST
def ask(request):
    try:
        q = json.loads(request.body or b"{}").get("q", "")
    except ValueError:
        q = ""
    try:
        m = services.ask(request.user, q)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    return JsonResponse({"answer": _msg(m)})
