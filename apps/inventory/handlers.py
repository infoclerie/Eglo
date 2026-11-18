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
