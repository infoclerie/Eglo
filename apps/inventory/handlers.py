"""inventory modülünün dinlediği olaylar."""
from apps.core.events import subscribe

from .models import StockCount


@subscribe("approval.approved.inventory.count_adjust")
def on_count_approved(request, user=None, **kw):
    from .services import apply_count
    apply_count(StockCount.objects.get(pk=request.target_id), user=user)


@subscribe("approval.rejected.inventory.count_adjust")
def on_count_rejected(request, **kw):
    StockCount.objects.filter(pk=request.target_id).update(status="rejected")


@subscribe("core.collect_activity")
def activity_rows(start, end, q, user_id, source, extra, **kw):
    """İşlem geçmişi: stok hareketleri."""
    if source not in ("", "stok") or extra.get("account"):
        return []
    from django.db.models import Q

    from .models import StockMove
    qs = StockMove.objects.select_related("product", "source", "destination", "lot", "user").filter(date__date__gte=start, date__date__lte=end)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if q:
        qs = qs.filter(Q(product__sku__icontains=q) | Q(product__name__icontains=q) | Q(reference__icontains=q) | Q(lot__lot_no__icontains=q))
    return [{"at": m.date, "source": "stok", "user": m.user, "action": m.get_move_type_display(),
             "text": f"{m.product.sku} · {m.product.name} × {m.quantity.normalize():f}",
             "detail": f"{m.source.code} → {m.destination.code}" + (f" · LOT {m.lot.lot_no}" if m.lot else "") + (f" · {m.reference}" if m.reference else ""),
             "level": ""} for m in qs.order_by("-date")[:300]]
