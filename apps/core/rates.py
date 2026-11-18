"""
Döviz ve altın kurları (üst şerit). 5 dakika önbellek.
Kaynak 1: finans.truncgil.com/v4/today.json (USD, EUR, gram altın; yanıt bazen yarım geldiği için alan alan okunur)
Kaynak 2 (yedek, USD/EUR): TCMB today.xml (resmi, günlük)
"""
import re
from xml.etree import ElementTree as ET

import requests
from django.core.cache import cache

TRUNCGIL = "https://finans.truncgil.com/v4/today.json"
TCMB = "https://www.tcmb.gov.tr/kurlar/today.xml"
ITEMS = [("USD", "Dolar"), ("EUR", "Euro"), ("GRA", "Gram altın")]


def _num(block, key):
    m = re.search(rf'"{key}"\s*:\s*(-?[\d.]+)', block)
    return float(m.group(1)) if m else None


def fetch():
    out = {}
    try:
        text = requests.get(TRUNCGIL, timeout=4, headers={"User-Agent": "EgloERP"}).text
        for code, label in ITEMS:
            m = re.search(rf'"{code}"\s*:\s*\{{([^}}]*)\}}', text)
            if m and _num(m.group(1), "Selling"):
                out[code] = {"label": label, "buy": _num(m.group(1), "Buying"), "sell": _num(m.group(1), "Selling"),
                             "change": _num(m.group(1), "Change") or 0}
    except requests.RequestException:
        pass
    if "USD" not in out or "EUR" not in out:
        try:
            root = ET.fromstring(requests.get(TCMB, timeout=4).content)
            for cur in root.findall("Currency"):
                code = cur.get("CurrencyCode")
                if code in ("USD", "EUR") and code not in out:
                    out[code] = {"label": dict(ITEMS)[code], "buy": float(cur.findtext("ForexBuying")),
                                 "sell": float(cur.findtext("ForexSelling")), "change": 0}
        except (requests.RequestException, ET.ParseError, TypeError, ValueError):
            pass
    return [{"code": c, **out[c]} for c, _ in ITEMS if c in out]


def get_rates():
    data = cache.get("erp_rates")
    if data is None:
        data = fetch()
        cache.set("erp_rates", data, 300 if data else 60)
    return data
