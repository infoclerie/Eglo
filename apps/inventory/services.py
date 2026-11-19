"""
Stok iş kuralları — stok miktarını DEĞİŞTİREN tek yer burasıdır.
Diğer modüller (satış, satın alma, sevkiyat, üretim) bu fonksiyonları veya olayları kullanır;
Quant/StockMove tablolarına doğrudan yazmaz. Formüller ve kurallar: apps/inventory/MODULE.md
"""
from datetime import timedelta
from decimal import ROUND_FLOOR, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.core.approvals import request_approval
from apps.core.events import publish
from apps.core.models import Sequence, Setting

from .models import Location, Lot, Quant, Reservation, StockCount, StockCountLine, StockMove, Warehouse

D = Decimal
ZERO = D("0")

DEFAULT_EXPIRY_THRESHOLDS = {"info": 180, "warning": 120, "critical": 90, "approval": 30}
EXPIRY_LABELS = {
    "ok": "Normal", "info": "Bilgilendirme", "warning": "Yaklaşan SKT", "critical": "Kritik SKT",
    "approval": "Yönetici onayı gerekli", "expired": "SKT geçmiş — satış/sevk blokajı",
}


class InsufficientStock(ValidationError):
    pass


# ---------------------------------------------------------------- yardımcılar

def expiry_thresholds():
    t = dict(DEFAULT_EXPIRY_THRESHOLDS)
    t.update(Setting.get("inventory.expiry_thresholds", {}) or {})
    return t


def expiry_status(lot, today=None):
    """SKT'ye kalan güne göre durum kodu (eşikler Sistem ayarları > inventory.expiry_thresholds)."""
    if lot is None or lot.expiry_date is None:
        return None
    days = lot.days_to_expiry(today)
    t = expiry_thresholds()
    if days < 0:
        return "expired"
    for code in ("approval", "critical", "warning", "info"):
        if days <= t[code]:
            return code
    return "ok"


def virtual_location(kind):
    names = dict(Location.KIND)
    loc, _ = Location.objects.get_or_create(
        code=f"V-{kind.upper()}",
        defaults={"kind": kind, "name": names[kind], "is_sellable": False, "can_pick": False},
    )
    return loc


def _lock_quant(product, location, lot=None, pallet=None, create=False):
    qs = Quant.objects.select_for_update(of=("self",)).filter(
        product=product, location=location, lot=lot, pallet=pallet)
    quant = qs.first()
    if quant is None and create:
        quant = Quant.objects.create(product=product, location=location, lot=lot, pallet=pallet)
    return quant


# ---------------------------------------------------------------- temel hareket

@transaction.atomic
def move_stock(product, quantity, source, destination, move_type, lot=None, pallet=None,
               reference="", user=None, note="", unit_cost=None, consume_reserved=False):
    qty = D(str(quantity))
    if qty <= 0:
        raise ValidationError("Miktar sıfırdan büyük olmalı.")
    if product.is_kit:
        raise ValidationError("Set ürün fiziksel stok tutmaz; bileşenleri hareket ettirin.")
    if source.pk == destination.pk:
        raise ValidationError("Kaynak ve hedef lokasyon aynı olamaz.")
    if source.is_virtual and destination.is_virtual:
        raise ValidationError("İki sanal lokasyon arasında hareket yapılamaz.")
    if product.track_lot and lot is None:
        raise ValidationError(f"{product.sku} için LOT numarası zorunlu.")
    if lot is not None and lot.product_id != product.pk:
        raise ValidationError("LOT bu ürüne ait değil.")
    if lot is not None and destination.is_sellable and expiry_status(lot) == "expired":
        raise ValidationError(f"SKT'si geçmiş LOT ({lot.lot_no}) satışa uygun lokasyona alınamaz.")

    if not source.is_virtual:
        quant = _lock_quant(product, source, lot, pallet)
        free = ZERO if quant is None else (quant.quantity if consume_reserved else quant.free_quantity)
        if free < qty:
            raise InsufficientStock(
                f"{product.sku} için {source} lokasyonunda yeterli stok yok (kullanılabilir {free}, istenen {qty}).")
        quant.quantity -= qty
        if consume_reserved:
            quant.reserved_quantity -= qty
        quant.save(update_fields=["quantity", "reserved_quantity", "updated_at"])

    if not destination.is_virtual:
        quant = _lock_quant(product, destination, lot, pallet, create=True)
        quant.quantity += qty
        quant.save(update_fields=["quantity", "updated_at"])

    move = StockMove.objects.create(
        move_type=move_type, product=product, quantity=qty, source=source, destination=destination,
        lot=lot, pallet=pallet, reference=reference, note=note, user=user,
        unit_cost=product.cost if unit_cost is None else unit_cost,
    )
    publish("inventory.stock_moved", move=move)
    return move


@transaction.atomic
def receive(product, quantity, location, lot_no=None, expiry_date=None, production_date=None,
            producer="", reference="", user=None, unit_cost=None, move_type="purchase_in", pallet=None):
    """Mal kabul / üretimden giriş. LOT yoksa oluşturur; SKT verilmemişse raf ömründen hesaplar."""
    lot = None
    if product.track_lot:
        if not lot_no:
            raise ValidationError("Mal kabulde LOT numarası zorunlu.")
        if expiry_date is None and production_date and product.shelf_life_days:
            expiry_date = production_date + timedelta(days=product.shelf_life_days)
        lot, created = Lot.objects.get_or_create(
            product=product, lot_no=lot_no,
            defaults={"expiry_date": expiry_date, "production_date": production_date, "producer": producer})
        if not created and expiry_date and lot.expiry_date and lot.expiry_date != expiry_date:
            raise ValidationError(f"LOT {lot_no} sistemde farklı SKT ile kayıtlı ({lot.expiry_date}).")
    source = virtual_location({"production_in": "production", "count_adjust": "adjustment"}.get(move_type, "supplier"))
    if unit_cost is not None:
        from apps.catalog.services import update_average_cost
        on_hand = Quant.objects.filter(product=product).aggregate(s=Sum("quantity"))["s"] or ZERO
        update_average_cost(product, on_hand, quantity, unit_cost)
    return move_stock(product, quantity, source, location, move_type, lot=lot, pallet=pallet,
                      reference=reference, user=user, unit_cost=unit_cost)


def transfer(product, quantity, source, destination, lot=None, pallet=None, reference="", user=None, note=""):
    return move_stock(product, quantity, source, destination, "transfer", lot=lot, pallet=pallet,
                      reference=reference, user=user, note=note)


def scrap(product, quantity, source, lot=None, reference="", user=None, note=""):
    return move_stock(product, quantity, source, virtual_location("scrap"), "scrap", lot=lot,
                      reference=reference, user=user, note=note)


# ---------------------------------------------------------------- rezervasyon (FEFO)

def _candidate_quants(product, warehouse=None, allow_near_expiry=False, today=None):
    today = today or timezone.localdate()
    qs = Quant.objects.select_for_update(of=("self",)).select_related("lot", "location").filter(
        product=product, location__is_sellable=True, location__active=True,
        quantity__gt=F("reserved_quantity"),
    ).exclude(lot__expiry_date__lt=today)
    if not allow_near_expiry:
        limit = today + timedelta(days=expiry_thresholds()["approval"])
        qs = qs.exclude(lot__expiry_date__lte=limit)
    if warehouse is not None:
        qs = qs.filter(location__warehouse=warehouse)
    # FEFO: SKT'si en yakın önce; SKT yoksa en eski giriş önce (FIFO)
    return qs.order_by(F("lot__expiry_date").asc(nulls_last=True), "lot__received_at", "id")


@transaction.atomic
def reserve(product, quantity, reference, warehouse=None, allow_near_expiry=False):
    """Stok ayırır. Yetmezse hiçbir şey ayırmadan InsufficientStock fırlatır (fazla satış engeli)."""
    qty = D(str(quantity))
    if product.is_kit:
        result = []
        for comp in product.components.select_related("component"):
            result += reserve(comp.component, qty * comp.quantity, reference, warehouse, allow_near_expiry)
        return result
    need, result = qty, []
    for quant in _candidate_quants(product, warehouse, allow_near_expiry):
        take = min(quant.free_quantity, need)
        quant.reserved_quantity += take
        quant.save(update_fields=["reserved_quantity", "updated_at"])
        result.append(Reservation.objects.create(reference=reference, product=product, quant=quant, quantity=take))
        need -= take
        if need <= 0:
            break
    if need > 0:
        raise InsufficientStock(f"{product.sku}: {qty} istendi, satışa uygun stok {qty - need}.")
    publish("inventory.reserved", reference=reference, product=product, quantity=qty)
    return result


@transaction.atomic
def release(reference):
    released = ZERO
    for r in Reservation.objects.filter(reference=reference):
        quant = Quant.objects.select_for_update().get(pk=r.quant_id)
        quant.reserved_quantity -= r.quantity
        quant.save(update_fields=["reserved_quantity", "updated_at"])
        released += r.quantity
        r.delete()
    publish("inventory.released", reference=reference)
    return released


@transaction.atomic
def ship_reserved(reference, user=None, destination=None, move_type="sale_out"):
    """Rezerve edilen stoğu müşteriye çıkarır (stok düşer). Sevkiyat modülü çağırır."""
    reservations = list(Reservation.objects.select_related("quant", "product").filter(reference=reference))
    if not reservations:
        raise ValidationError(f"{reference} için rezervasyon yok.")
    destination = destination or virtual_location("customer")
    moves = []
    for r in reservations:
        q = r.quant
        moves.append(move_stock(r.product, r.quantity, q.location, destination, move_type, lot=q.lot,
                                pallet=q.pallet, reference=reference, user=user, consume_reserved=True))
        r.delete()
    publish("inventory.shipped", reference=reference, moves=moves)
    return moves


def reservations_for(reference):
    """Bir referansın rezervasyonları (toplama listesi için), lokasyon koduna göre sıralı."""
    return [{"product": r.product, "location": r.quant.location, "lot": r.quant.lot, "pallet": r.quant.pallet,
             "quantity": r.quantity}
            for r in Reservation.objects.select_related("product", "quant__location", "quant__lot", "quant__pallet")
            .filter(reference=reference).order_by("quant__location__code")]


def shipped_lots(reference, product):
    """Bir siparişle sevk edilen LOT'lar ve miktarları (iade kabulünde LOT bulmak için)."""
    rows = (StockMove.objects.filter(reference=reference, product=product, move_type="sale_out")
            .values("lot").annotate(q=Sum("quantity")).order_by("lot"))
    return [(Lot.objects.get(pk=r["lot"]) if r["lot"] else None, r["q"]) for r in rows]


@transaction.atomic
def receive_customer_return(product, quantity, location, lot=None, reference="", user=None):
    """Müşteri iadesi: sanal müşteri lokasyonundan iade kontrol alanına giriş."""
    return move_stock(product, quantity, virtual_location("customer"), location, "customer_return",
                      lot=lot, reference=reference, user=user)


def find_location(warehouse, kind):
    qs = Location.objects.filter(kind=kind, active=True)
    if warehouse is not None:
        qs = qs.filter(warehouse=warehouse)
    loc = qs.order_by("code").first()
    if loc is None:
        raise ValidationError(f"Depoda '{dict(Location.KIND)[kind]}' türünde lokasyon tanımlı değil.")
    return loc


# ---------------------------------------------------------------- stok durumu

def stock_summary(product, warehouse=None, today=None):
    """Müşteri dokümanı §4.2: ürün bazında stok durumları."""
    today = today or timezone.localdate()
    if product.is_kit:
        comps = list(product.components.select_related("component"))
        avail = min((stock_summary(c.component, warehouse, today)["available"] / c.quantity)
                    .to_integral_value(ROUND_FLOOR) for c in comps) if comps else ZERO
        return {"available": avail, "is_kit": True}
    qs = Quant.objects.filter(product=product)
    if warehouse is not None:
        qs = qs.filter(location__warehouse=warehouse)
    rows = qs.values("location__kind", "location__is_sellable", "lot__expiry_date", "quantity", "reserved_quantity")
    s = {k: ZERO for k in ("physical", "available", "reserved", "expired", "quarantine", "damaged",
                           "return_check", "shipping", "receiving", "sample", "transit", "storage")}
    for r in rows:
        qty, res = r["quantity"], r["reserved_quantity"]
        s["physical"] += qty
        s["reserved"] += res
        s[r["location__kind"]] = s.get(r["location__kind"], ZERO) + qty
        expired = r["lot__expiry_date"] is not None and r["lot__expiry_date"] < today
        if r["location__is_sellable"]:
            if expired:
                s["expired"] += qty
            else:
                s["available"] += qty - res
    s["incoming"] = sum((x or ZERO for x in publish("inventory.collect_incoming", product=product)), ZERO)
    s["is_kit"] = False
    return s


def low_stock_products(products=None):
    """Satışa uygun stoğu minimum seviyenin altına düşen ürünler."""
    from apps.catalog.models import Product
    products = products if products is not None else Product.objects.filter(active=True, min_stock__gt=0).exclude(kind="kit")
    out = []
    for p in products:
        avail = stock_summary(p)["available"]
        if avail < p.min_stock:
            out.append((p, avail))
    return out


def expiring_lots(within_days=None, today=None):
    """Stokta olan ve SKT'si yaklaşan/geçmiş LOT'lar (FEFO sırasıyla)."""
    today = today or timezone.localdate()
    within_days = expiry_thresholds()["critical"] if within_days is None else within_days
    return (Lot.objects.filter(expiry_date__lte=today + timedelta(days=within_days), quants__quantity__gt=0)
            .annotate(on_hand=Sum("quants__quantity")).select_related("product").order_by("expiry_date"))


# ---------------------------------------------------------------- satın alma önerisi

def suggest_purchase_qty(avg_daily_sales, lead_time_days, safety_stock, available, incoming=0):
    """
    Önerilen ihtiyaç = (günlük ortalama satış × tedarik süresi) + güvenlik stoğu − kullanılabilir stok − yoldaki/sipariş verilmiş
    Doküman örneği: (20 × 15) + 100 − 250 = 150. Sonuç negatifse 0.
    """
    need = D(str(avg_daily_sales)) * D(str(lead_time_days)) + D(str(safety_stock)) - D(str(available)) - D(str(incoming))
    return max(need, ZERO).to_integral_value(rounding="ROUND_CEILING")


def average_daily_sales(product, days=90, today=None):
    since = timezone.now() - timedelta(days=days)
    out = StockMove.objects.filter(product=product, move_type="sale_out", date__gte=since).aggregate(s=Sum("quantity"))["s"] or ZERO
    back = StockMove.objects.filter(product=product, move_type="customer_return", date__gte=since).aggregate(s=Sum("quantity"))["s"] or ZERO
    return max(out - back, ZERO) / D(days)


def purchase_suggestion(product, days=90):
    """Öneri otomatik siparişe dönüşmez; satın alma modülünde yetkili onayıyla siparişe çevrilir."""
    summary = stock_summary(product)
    avg = average_daily_sales(product, days)
    qty = suggest_purchase_qty(avg, product.lead_time_days, product.safety_stock, summary["available"], summary["incoming"])
    return {"product": product, "avg_daily_sales": avg.quantize(D("0.01")), "lead_time_days": product.lead_time_days,
            "safety_stock": product.safety_stock, "available": summary["available"], "incoming": summary["incoming"],
            "suggested_qty": qty}


# ---------------------------------------------------------------- sayım

@transaction.atomic
def start_count(warehouse, kind="general", locations=None, products=None, user=None):
    count = StockCount.objects.create(number=Sequence.next("inventory.count", "SAY-"), warehouse=warehouse, kind=kind)
    qs = Quant.objects.filter(location__warehouse=warehouse, quantity__gt=0)
    if locations:
        qs = qs.filter(location__in=locations)
    if products:
        qs = qs.filter(product__in=products)
    agg = qs.values("product", "location", "lot").annotate(total=Sum("quantity"))
    StockCountLine.objects.bulk_create([
        StockCountLine(count=count, product_id=r["product"], location_id=r["location"], lot_id=r["lot"],
                       system_quantity=r["total"]) for r in agg])
    return count


@transaction.atomic
def submit_count(count, user=None):
    if count.status != "draft":
        raise ValidationError("Sadece taslak sayım onaya gönderilebilir.")
    if count.lines.filter(counted_quantity__isnull=True).exists():
        raise ValidationError("Sayılmamış satırlar var.")
    count.status = "submitted"
    count.save(update_fields=["status", "updated_at"])
    diffs = [l for l in count.lines.all() if l.difference]
    return request_approval("inventory.count_adjust", count, f"Sayım farkı düzeltme: {count.number}", user,
                            payload={"lines_with_difference": len(diffs)})


@transaction.atomic
def apply_count(count, user=None):
    if count.status != "submitted":
        raise ValidationError("Sayım onay bekleme durumunda değil.")
    adj = virtual_location("adjustment")
    for line in count.lines.select_related("product", "location", "lot"):
        diff = line.difference
        if not diff:
            continue
        if diff > 0:
            move_stock(line.product, diff, adj, line.location, "count_adjust", lot=line.lot, reference=count.number, user=user)
        else:
            move_stock(line.product, -diff, line.location, adj, "count_adjust", lot=line.lot, reference=count.number, user=user)
    count.status = "applied"
    count.save(update_fields=["status", "updated_at"])
    publish("inventory.count_applied", count=count)
    return count


# ---------------------------------------------------------------- ilk kurulum
DEFAULT_AREAS = [("A-KABUL", "Mal kabul alanı", "receiving"), ("A-SEVK", "Sevkiyat alanı", "shipping"),
                 ("A-IADE", "İade alanı", "return_check"), ("A-KARANTINA", "Karantina alanı", "quarantine"),
                 ("A-HASAR", "Hasarlı ürün alanı", "damaged"), ("A-NUMUNE", "Numune alanı", "sample")]


@transaction.atomic
def ensure_default_warehouse(aisles=2, racks=3, levels=2):
    """Hiç depo yoksa 'A · Ana depo' ve temel alanlarla örnek raf lokasyonlarını (A-01-01-01 ...) oluşturur. Döner: (depo, yeni_mi)"""
    if Warehouse.objects.exists():
        return Warehouse.objects.order_by("code").first(), False
    wh = Warehouse.objects.create(code="A", name="Ana depo")
    for code, name, kind in DEFAULT_AREAS:
        Location.objects.create(code=code, warehouse=wh, name=name, kind=kind)
    for a in range(1, aisles + 1):
        for r in range(1, racks + 1):
            for lv in range(1, levels + 1):
                Location.objects.create(code=f"A-{a:02d}-{r:02d}-{lv:02d}", warehouse=wh, kind="storage",
                                        aisle=f"{a:02d}", rack=f"{r:02d}", level=f"{lv:02d}")
    return wh, True
