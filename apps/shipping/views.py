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
                services.scan(sh, request.POST["code"].strip(), (request.POST.get("qty") or "1").replace(",", "."), request.user)
            elif action == "pack":
                w = (request.POST.get("weight") or "").replace(",", ".") or None
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


@login_required
@permission_required("shipping.view_shipment", raise_exception=True)
def labels(request, pk=None):
    """10×15 cm kargo etiketi (koli başına bir etiket). Toplu: ?ids=1,2,3"""
    from apps.core.models import Setting
    ids = [pk] if pk else [int(x) for x in request.GET.get("ids", "").split(",") if x.strip().isdigit()]
    out = []
    for sh in Shipment.objects.select_related("order", "order__channel").filter(pk__in=ids).order_by("pk"):
        total = max(sh.package_count, 1)
        code = sh.tracking_no or sh.number
        out.extend({"sh": sh, "no": i, "total": total, "code": code if total == 1 else f"{code}-{i}"} for i in range(1, total + 1))
    return render(request, "shipping/label.html", {"labels": out, "company": Setting.get("accounting.company", {}) or {}})
