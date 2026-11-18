from decimal import Decimal

from apps.core.events import publish

ZERO = Decimal("0")


def open_balance(partner):
    """
    Carinin açık bakiyesi (alacak +). Muhasebe modülü `partners.collect_balance` olayına bakiye döndürür;
    muhasebe kapalıysa 0 kabul edilir.
    """
    return sum((x or ZERO for x in publish("partners.collect_balance", partner=partner)), ZERO)


def credit_check(partner, amount):
    """Kredi limiti kontrolü: limit 0 ise kontrol yok. Döner: (uygun_mu, açık_bakiye, limit)"""
    balance = open_balance(partner)
    limit = partner.credit_limit or ZERO
    ok = limit <= 0 or balance + Decimal(str(amount)) <= limit
    return ok, balance, limit
