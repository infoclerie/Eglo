"""
Olay yolu (event bus) — modüller birbirini DOĞRUDAN çağırmaz, olay yayınlar.

    from apps.core.events import publish, subscribe

    @subscribe("sales.order_confirmed")
    def reserve_stock(order, **kw): ...

    publish("sales.order_confirmed", order=order)

- Dinleyiciler modülün `handlers.py` dosyasında tanımlanır ve AppConfig.ready() içinde import edilir.
- Modül kapalıysa handlers.py yüklenmez → o modülün tepkisi devre dışı kalır, diğerleri bozulmaz.
- Dinleyiciler SENKRON ve aynı veritabanı işlemi (transaction) içinde çalışır: biri hata verirse
  bütün işlem geri alınır (stok/fatura tutarlılığı için bilinçli tercih). Dış sistemlere (pazaryeri,
  kargo, e-fatura) yapılacak çağrılar ileride "outbox" kuyruğu ile işlem sonrasına alınacaktır.

Olay adları ve yükleri her modülün MODULE.md dosyasında belgelenir.
"""
import logging
from collections import defaultdict

log = logging.getLogger("erp.events")
_handlers = defaultdict(list)


def subscribe(event_name):
    def decorator(func):
        if func not in _handlers[event_name]:
            _handlers[event_name].append(func)
        return func
    return decorator


def publish(event_name, **payload):
    results = []
    for handler in list(_handlers.get(event_name, [])):
        log.debug("event %s -> %s", event_name, handler.__qualname__)
        results.append(handler(**payload))
    return results


def handlers_for(event_name):
    return list(_handlers.get(event_name, []))
