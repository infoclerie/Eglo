"""
Excel ile toplu yükleme: ürün kartları, fiyatlar, stok girişi.
Akış: şablon indir → doldur → yükle → ÖNİZLEME (satır satır hata) → onayla → tek işlemde kaydet (hata varsa hiçbir şey yazılmaz).
Stok yalnız inventory.services.receive ile girer (hareket türü: Sayım farkı / açılış).
"""
import datetime as dt
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import Brand, Category, Product, ProductPrice, SalesChannel


def _choices(field):
    return {**{str(k).lower(): k for k, _ in field.choices}, **{str(v).lower(): k for k, v in field.choices}}


def product_columns():
    f = Product._meta.get_field
    return [
        ("sku", "Ürün kodu (SKU)*", "text"), ("name", "Ürün adı*", "text"), ("barcode", "Barkod", "text"),
        ("brand", "Marka", "text"), ("category", "Kategori", "text"),
        ("kind", "Tür", ("choice", f("kind"))), ("group", "Ürün grubu", ("choice", f("group"))), ("unit", "Birim", ("choice", f("unit"))),
        ("volume", "Hacim / ağırlık", "text"), ("weight_kg", "Birim ağırlık (kg)", "dec"),
        ("units_per_case", "Koli içi adet", "int"), ("case_barcode", "Koli barkodu", "text"),
        ("cost", "Maliyet (KDV hariç)", "dec"), ("list_price", "Liste fiyatı (KDV hariç)", "dec"), ("vat_rate", "KDV %", "dec"),
        ("min_stock", "Minimum stok", "dec"), ("safety_stock", "Güvenlik stoğu", "dec"), ("lead_time_days", "Tedarik süresi (gün)", "int"),
        ("track_lot", "LOT/SKT takibi (Evet/Hayır)", "bool"), ("shelf_life_days", "Raf ömrü (gün)", "int"), ("active", "Aktif (Evet/Hayır)", "bool"),
    ]


def price_columns():
    cols = [("sku", "Ürün kodu (SKU) veya barkod*", "text"), ("list_price", "Liste fiyatı (KDV hariç)", "dec"), ("cost", "Maliyet (KDV hariç)", "dec")]
    cols += [(f"ch:{c.code}", f"Fiyat: {c.name}", "dec") for c in SalesChannel.objects.order_by("name")]
    return cols


def stock_columns():
    return [("sku", "Ürün kodu (SKU) veya barkod*", "text"), ("location", "Lokasyon kodu*", "text"), ("quantity", "Adet*", "dec"),
            ("lot_no", "LOT / parti no", "text"), ("expiry_date", "SKT (gg.aa.yyyy)", "date"),
            ("production_date", "Üretim tarihi", "date"), ("unit_cost", "Birim maliyet", "dec")]


KINDS = {
    "urun": {"title": "Ürün kartları", "desc": "Yeni ürün ekler, SKU'su olanı günceller. Boş hücre mevcut değeri değiştirmez.", "cols": product_columns},
    "fiyat": {"title": "Fiyatlar", "desc": "Liste fiyatı, maliyet ve kanal fiyatlarını (Trendyol, Hepsiburada, web, bayi...) toplu günceller.", "cols": price_columns},
    "stok": {"title": "Stok girişi (açılış / toplu giriş)", "desc": "Lokasyona LOT ve SKT ile stok ekler. Mevcut stoğun üstüne eklenir.", "cols": stock_columns},
}

EXAMPLES = {
    "urun": {"sku": "CLR-SRM-30", "name": "Clerie Serum 30 ml", "barcode": "8690000000017", "brand": "Clerie", "kind": "Standart ürün",
             "group": "Kozmetik", "unit": "Adet", "volume": "30 ml", "weight_kg": 0.08, "units_per_case": 24, "cost": 45, "list_price": 120,
             "vat_rate": 20, "track_lot": "Evet", "shelf_life_days": 730, "active": "Evet"},
    "fiyat": {"sku": "CLR-SRM-30", "list_price": 120, "cost": 45},
    "stok": {"sku": "CLR-SRM-30", "location": "A-01-01-01", "quantity": 240, "lot_no": "L2611", "expiry_date": "30.11.2028"},
}


def template_xlsx(kind):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    cols = KINDS[kind]["cols"]()
    wb = Workbook()
    ws = wb.active
    ws.title = "Veri"
    ws.append([c[1] for c in cols])
    ex = EXAMPLES.get(kind, {})
    ws.append([ex.get(c[0], "") for c in cols])
    for i, c in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="15803D")
        ws.column_dimensions[get_column_letter(i)].width = max(14, len(c[1]) + 2)
        if isinstance(c[2], tuple):
            dv = DataValidation(type="list", formula1='"' + ",".join(str(v) for _, v in c[2][1].choices) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{get_column_letter(i)}2:{get_column_letter(i)}5000")
    ws.freeze_panes = "A2"
    info = wb.create_sheet("Açıklama")
    info.append(["2. satır örnektir; silip kendi verinizi yazın. * işaretli sütunlar zorunludur."])
    info.append(["Sayılarda virgül veya nokta kullanabilirsiniz (12,50 = 12.50). Tarih: gg.aa.yyyy."])
    if kind == "urun":
        info.append(["Aynı SKU sistemde varsa ürün GÜNCELLENİR; boş bırakılan hücreler mevcut değeri korur."])
    if kind == "stok":
        info.append(["LOT/SKT takibi açık ürünlerde LOT no zorunludur. Stok mevcut miktarın ÜSTÜNE eklenir."])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _dec(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    s = str(v).strip().replace(" ", "")
    if "," in s and "." in s:  # 1.234,56 → 1234.56
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"'{v}' sayı değil")


def _date(v):
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"'{v}' tarih değil (gg.aa.yyyy)")


def _bool(v):
    if v in (None, ""):
        return None
    s = str(v).strip().lower()
    if s in ("evet", "e", "1", "true", "var", "x", "yes"):
        return True
    if s in ("hayır", "hayir", "h", "0", "false", "yok", "no"):
        return False
    raise ValueError(f"'{v}' Evet/Hayır olmalı")


def _convert(kind, value):
    if isinstance(value, str):
        value = value.strip()
    if kind == "text":
        if value in (None, ""):
            return None
        if isinstance(value, float) and value.is_integer():
            value = int(value)  # Excel barkodu sayı olarak tutabilir
        return str(value).strip()
    if kind == "dec":
        return _dec(value)
    if kind == "int":
        d = _dec(value)
        return None if d is None else int(d)
    if kind == "date":
        return _date(value)
    if kind == "bool":
        return _bool(value)
    if isinstance(kind, tuple):
        if value in (None, ""):
            return None
        m = _choices(kind[1]).get(str(value).lower())
        if m is None:
            raise ValueError(f"'{value}' geçersiz; seçenekler: {', '.join(str(v) for _, v in kind[1].choices)}")
        return m
    return value


def parse(kind, fileobj):
    """Döner: (satırlar [{"row": no, "data": {}, "errors": []}], uyarı listesi)"""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(fileobj, data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"Dosya okunamadı (.xlsx olmalı): {exc}")
    ws = wb.worksheets[0]
    cols = KINDS[kind]["cols"]()
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h or "").strip().rstrip("*").strip().lower() for h in next(rows_iter, [])]
    index = {}
    for key, label, typ in cols:
        name = label.rstrip("*").strip().lower()
        if name in header:
            index[key] = (header.index(name), typ)
    missing = [label for key, label, _ in cols if label.endswith("*") and key not in index]
    if missing:
        raise ValidationError("Şablon sütunları bulunamadı: " + ", ".join(missing) + ". Lütfen bu sayfadan indirilen şablonu kullanın.")
    out = []
    for n, values in enumerate(rows_iter, start=2):
        if not values or all(v in (None, "") for v in values):
            continue
        data, errors = {}, []
        for key, (i, typ) in index.items():
            try:
                data[key] = _convert(typ, values[i] if i < len(values) else None)
            except ValueError as exc:
                errors.append(f"{dict((k, l) for k, l, _ in cols)[key].rstrip('*')}: {exc}")
        out.append({"row": n, "data": data, "errors": errors})
    if not out:
        raise ValidationError("Dosyada veri satırı yok.")
    validate(kind, out)
    return out


def validate(kind, rows):
    """İş kuralı kontrolleri (satır hatası olarak eklenir) + her satıra 'action' (ekle/güncelle) yazar."""
    from apps.catalog.services import find_product
    from apps.inventory.models import Location
    seen = set()
    for r in rows:
        d, e = r["data"], r["errors"]
        if kind == "urun":
            if not d.get("sku"):
                e.append("SKU boş")
                continue
            if d["sku"] in seen:
                e.append("Dosyada aynı SKU iki kez var")
            seen.add(d["sku"])
            existing = Product.objects.filter(sku=d["sku"]).first()
            r["action"] = "Güncelle" if existing else "Yeni ürün"
            if not existing and not d.get("name"):
                e.append("Yeni üründe ürün adı zorunlu")
            for f in ("barcode", "case_barcode"):
                if d.get(f) and Product.objects.filter(**{f: d[f]}).exclude(sku=d["sku"]).exists():
                    e.append(f"{'Barkod' if f == 'barcode' else 'Koli barkodu'} başka üründe kayıtlı: {d[f]}")
        else:
            p = find_product(d.get("sku") or "")[0] if d.get("sku") else None
            if p is None:
                e.append(f"Ürün bulunamadı: {d.get('sku') or '(boş)'}")
                continue
            r["product"] = f"{p.sku} · {p.name}"
            if kind == "stok":
                if not d.get("quantity") or d["quantity"] <= 0:
                    e.append("Adet sıfırdan büyük olmalı")
                loc = Location.objects.filter(code=d.get("location") or "").first()
                if loc is None or loc.is_virtual:
                    e.append(f"Lokasyon bulunamadı: {d.get('location') or '(boş)'}")
                if p.track_lot and not d.get("lot_no"):
                    e.append("Bu ürün LOT takipli; LOT no zorunlu")
                if p.is_kit:
                    e.append("Set ürüne stok girilmez; bileşenlerine girin")
                r["action"] = "Stok girişi"
            else:
                r["action"] = "Fiyat güncelle"
    return rows


@transaction.atomic
def apply(kind, rows, user=None):
    """Hatasız satırları yazar. Herhangi bir satırda hata varsa hiçbir şey yazmaz."""
    bad = [r for r in rows if r["errors"]]
    if bad:
        raise ValidationError(f"{len(bad)} satırda hata var; önce dosyayı düzeltin.")
    from apps.catalog.services import find_product
    counts = {"created": 0, "updated": 0}
    for r in rows:
        d = {k: v for k, v in r["data"].items() if v is not None}
        if kind == "urun":
            if "brand" in d:
                d["brand"] = Brand.objects.filter(name__iexact=d["brand"]).first() or Brand.objects.create(name=d["brand"])
            if "category" in d:
                d["category"] = (Category.objects.filter(name__iexact=d["category"]).first()
                                 or Category.objects.create(name=d["category"]))
            p = Product.objects.filter(sku=d["sku"]).first()
            if p is None:
                Product.objects.create(**d)
                counts["created"] += 1
            else:
                for k, v in d.items():
                    setattr(p, k, v)
                p.save()
                counts["updated"] += 1
        elif kind == "fiyat":
            p = find_product(d["sku"])[0]
            for k in ("list_price", "cost"):
                if k in d:
                    setattr(p, k, d[k])
            p.save()
            for k, v in d.items():
                if k.startswith("ch:"):
                    ch = SalesChannel.objects.get(code=k[3:])
                    ProductPrice.objects.update_or_create(product=p, channel=ch, defaults={"price": v})
            counts["updated"] += 1
        else:
            from apps.inventory import services as inventory
            from apps.inventory.models import Location
            p = find_product(d["sku"])[0]
            inventory.receive(p, d["quantity"], Location.objects.get(code=d["location"]), lot_no=d.get("lot_no"),
                              expiry_date=d.get("expiry_date"), production_date=d.get("production_date"),
                              reference="Excel toplu giriş", user=user, unit_cost=d.get("unit_cost"), move_type="count_adjust")
            counts["created"] += 1
    return counts
