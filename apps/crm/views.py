import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Activity, Opportunity


@login_required
@permission_required("crm.view_opportunity", raise_exception=True)
def board(request):
    cols = []
    opps = Opportunity.objects.select_related("partner", "owner")
    if request.GET.get("mine"):
        opps = opps.filter(owner=request.user)
    for code, label in Opportunity.STAGES:
        items = [o for o in opps if o.stage == code]
        cols.append({"code": code, "label": label, "items": items, "total": sum(o.expected_amount for o in items)})
    return render(request, "crm/board.html", {"cols": cols})


@login_required
@permission_required("crm.change_opportunity", raise_exception=True)
@require_POST
def move(request):
    data = json.loads(request.body or "{}")
    opp = get_object_or_404(Opportunity, pk=data.get("id"))
    try:
        services.move_stage(opp, data.get("stage"), request.user)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": " ".join(exc.messages)}, status=400)
    return JsonResponse({"ok": True})


@login_required
@permission_required("crm.view_activity", raise_exception=True)
def activities(request):
    if request.method == "POST" and request.user.has_perm("crm.change_activity"):
        Activity.objects.filter(pk=request.POST.get("done")).update(done=True)
        messages.success(request, "Takip tamamlandı.")
        return redirect(request.get_full_path())
    due = services.due_activities(request.user)
    upcoming = Activity.objects.filter(done=False).exclude(pk__in=due).select_related("partner", "opportunity")[:100]
    return render(request, "crm/activities.html", {"due": due, "upcoming": upcoming})


@login_required
@permission_required("crm.view_opportunity", raise_exception=True)
def segments(request):
    rows = services.segment_rows()
    seg = request.GET.get("s")
    counts = {}
    for r in rows:
        counts[r["segment"]] = counts.get(r["segment"], 0) + 1
    if seg:
        rows = [r for r in rows if r["segment"] == seg]
    return render(request, "crm/segments.html", {"rows": rows, "seg": seg, "counts": counts, "labels": services.SEGMENTS})
