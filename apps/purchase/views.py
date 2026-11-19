from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from apps.inventory.models import Location

from . import services
from .models import PurchaseOrder


@login_required
@permission_required("inventory.add_stockmove", raise_exception=True)
def receive(request, pk):
    """Satın alma siparişine karşı mal kabul (barkodlu terminalden de kullanılabilir)."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    locations = Location.objects.filter(active=True, warehouse=po.warehouse).exclude(kind__in=Location.VIRTUAL_KINDS)
    if request.method == "POST":
        line = get_object_or_404(po.lines, pk=request.POST["line"])
        try:
            services.receive_line(line, request.POST["quantity"].replace(",", "."), Location.objects.get(pk=request.POST["location"]),
                                  lot_no=request.POST.get("lot_no") or None,
                                  expiry_date=parse_date(request.POST.get("expiry_date") or ""),
                                  production_date=parse_date(request.POST.get("production_date") or ""),
                                  user=request.user, waybill_no=request.POST.get("waybill", ""))
            msg = f"{line.product.sku} teslim alındı."
            if request.FILES.getlist("photos"):
                from apps.catalog.views import save_photos
                msg += f" {save_photos(request, line.product, f'Mal kabul {po.number}')} fotoğraf eklendi."
            messages.success(request, msg)
        except (ValidationError, ValueError) as exc:
            messages.error(request, " ".join(getattr(exc, "messages", [str(exc)])))
        return redirect(request.path)
    return render(request, "purchase/receive.html", {"po": po, "lines": po.lines.select_related("product"),
                                                     "locations": locations})
