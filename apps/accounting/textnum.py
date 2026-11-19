"""Tutarı Türkçe yazıya çevirir (fatura 'Yalnız #...#' satırı): 1599.80 → 'Bin Beş Yüz Doksan Dokuz Türk Lirası Seksen Kuruş'."""
from decimal import ROUND_HALF_UP, Decimal

ONES = ["", "Bir", "İki", "Üç", "Dört", "Beş", "Altı", "Yedi", "Sekiz", "Dokuz"]
TENS = ["", "On", "Yirmi", "Otuz", "Kırk", "Elli", "Altmış", "Yetmiş", "Seksen", "Doksan"]
SCALES = ["", "Bin", "Milyon", "Milyar", "Trilyon"]


def _three(n):
    h, t, o = n // 100, (n // 10) % 10, n % 10
    out = []
    if h:
        out.append("Yüz" if h == 1 else f"{ONES[h]} Yüz")
    if t:
        out.append(TENS[t])
    if o:
        out.append(ONES[o])
    return " ".join(out)


def number_words(n):
    n = int(n)
    if n == 0:
        return "Sıfır"
    parts, i = [], 0
    while n:
        chunk = n % 1000
        if chunk:
            word = "Bin" if (i == 1 and chunk == 1) else (f"{_three(chunk)} {SCALES[i]}".strip())
            parts.append(word)
        n //= 1000
        i += 1
    return " ".join(reversed(parts))


def amount_words(amount, currency="TRY"):
    amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lira, kurus = int(amt), int((amt - int(amt)) * 100)
    unit = {"TRY": ("Türk Lirası", "Kuruş"), "USD": ("ABD Doları", "Sent"), "EUR": ("Avro", "Sent")}.get(currency, (currency, ""))
    text = f"{number_words(lira)} {unit[0]}"
    if kurus:
        text += f" {number_words(kurus)} {unit[1]}"
    return text
