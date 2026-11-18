from decimal import Decimal

from .models import Product


def update_average_cost(product, on_hand_qty, incoming_qty, incoming_unit_cost):
    """
    Ağırlıklı ortalama maliyet:
        yeni maliyet = (eldeki miktar × eski maliyet + gelen miktar × gelen birim maliyet) / (eldeki + gelen)
    Eldeki miktar 0 veya negatifse yeni maliyet = gelen birim maliyet.
    """
    on_hand, qty, cost = Decimal(str(on_hand_qty)), Decimal(str(incoming_qty)), Decimal(str(incoming_unit_cost))
    if qty <= 0:
        return product.cost
    if on_hand <= 0:
        new = cost
    else:
        new = (on_hand * product.cost + qty * cost) / (on_hand + qty)
    new = new.quantize(Decimal("0.01"))
    Product.objects.filter(pk=product.pk).update(cost=new)
    product.cost = new
    return new


def find_product(code):
    """SKU, ürün barkodu veya koli barkodu ile ürün bulur. Döner: (ürün, çarpan) — koli barkodunda çarpan = koli içi adet."""
    p = Product.objects.filter(barcode=code).first() or Product.objects.filter(sku=code).first()
    if p:
        return p, 1
    p = Product.objects.filter(case_barcode=code).first()
    return (p, p.units_per_case) if p else (None, 0)
