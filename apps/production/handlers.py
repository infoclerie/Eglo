"""production modülünün dinlediği olaylar."""
from apps.core.events import subscribe


@subscribe("inventory.collect_incoming")
def incoming(product, **kw):
    from .services import incoming_quantity
    return incoming_quantity(product)
