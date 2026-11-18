from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import CARRIERS, Shipment


@login_required
@permission_required("shipping.view_shipment", raise_exception=True)
def queue(request):
    qs = Shipment.objects.select_related("order", "order__channel").exclude(status__in=["delivered", "cancelled"])
    return render(request, "shipping/queue.html", {"shipments": qs[:300]})


@login_required
@permission_required("shipping.change_shipment", raise_exception=True)
def pick(request, pk):
    """El terminali ekranı: barkod okut → paketle → sevk et."""
    sh = get_object_or_404(Shipment.objects.select_related("order"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "scan":
                services.scan(sh, request.POST["code"].strip(), request.POST.get("qty") or 1, request.user)
            elif action == "pack":
                w = request.POST.get("weight") or None
                services.pack(sh, int(request.POST.get("packages") or 1), w, request.user)
            elif action == "ship":
                services.ship(sh, request.POST["carrier"], request.POST.get("tracking", ""), request.user,
                              request.POST.get("plate", ""), request.POST.get("driver", ""))
            elif action == "deliver":
                services.deliver(sh, request.POST.get("received_by", ""), request.POST.get("note", ""), request.user)
            messages.success(request, "Kaydedildi.")
        except (ValidationError, ValueError) as exc:
            messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(request.path)
    sh.refresh_from_db()
    lines = list(sh.lines.select_related("product", "location", "lot"))
    total = sum(l.quantity for l in lines) or 1
    progress = int(sum(l.picked_quantity for l in lines) * 100 / total)
    return render(request, "shipping/pick.html", {"sh": sh, "lines": lines, "carriers": CARRIERS, "progress": progress})
