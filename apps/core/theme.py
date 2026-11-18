"""Menü / vurgu rengi. Kullanıcı tercihi > şirket varsayılanı (Sistem ayarı `ui.default_color`) > mor."""
import re

DEFAULT = "#5b3a6e"
PRESETS = [("#5b3a6e", "Mor"), ("#1e3a5f", "Lacivert"), ("#1f2937", "Gece"), ("#0f766e", "Zümrüt"),
           ("#0b6bcb", "Okyanus"), ("#7f1d1d", "Bordo"), ("#c2410c", "Turuncu"), ("#374151", "Grafit"),
           ("#14532d", "Orman"), ("#6d28d9", "Lavanta")]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def valid(color):
    return bool(color and HEX.match(color))


def shade(color, factor):
    """factor < 1 koyulaştırır, > 1 açar (beyaza doğru)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    if factor <= 1:
        r, g, b = (int(c * factor) for c in (r, g, b))
    else:
        t = factor - 1
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def palette(color):
    color = color if valid(color) else DEFAULT
    return {"brand": color, "brand_600": shade(color, 0.8), "brand_50": shade(color, 1.92)}


def current(user):
    from .models import Setting, UserPreference
    pref = UserPreference.objects.filter(user=user).first() if getattr(user, "is_authenticated", False) else None
    color = pref.sidebar_color if pref and valid(pref.sidebar_color) else Setting.get("ui.default_color", DEFAULT)
    return palette(color)
