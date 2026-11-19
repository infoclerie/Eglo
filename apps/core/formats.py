"""Türkçe sayı/para biçimi: 4799.4 → '4.799,40 TL'."""
from decimal import Decimal


def num(value, digits=2):
    s = f"{Decimal(str(value or 0)):,.{digits}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def tl(value, digits=2):
    return f"{num(value, digits)} TL"
