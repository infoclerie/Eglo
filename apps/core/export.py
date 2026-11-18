"""Excel (.xlsx) dışa aktarma: tüm yönetim listeleri için 'Seçilenleri Excel'e aktar' eylemi ve filtreli listenin tamamı (?_export=xlsx)."""
import datetime as dt
import re
from decimal import Decimal

from django.contrib.admin.utils import label_for_field, lookup_field
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify

TAG = re.compile(r"<[^>]+>")


def _value(name, obj, modeladmin):
    try:
        field, attr, value = lookup_field(name, obj, modeladmin)
    except Exception:  # noqa: BLE001 — hesaplanamayan sütun boş geçer
        return ""
    if field is not None and getattr(field, "flatchoices", None):
        value = dict(field.flatchoices).get(value, value)
    if isinstance(value, bool):
        return "Evet" if value else "Hayır"
    if isinstance(value, dt.datetime):
        return timezone.localtime(value).replace(tzinfo=None) if timezone.is_aware(value) else value
    if isinstance(value, (int, float, Decimal, dt.date)) or value is None:
        return value
    return TAG.sub("", str(value))


def xlsx_response(modeladmin, request, queryset):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    model = modeladmin.model
    cols = [c for c in modeladmin.get_list_display(request) if c != "action_checkbox"]
    wb = Workbook()
    ws = wb.active
    ws.title = str(model._meta.verbose_name_plural)[:31]
    ws.append([str(label_for_field(c, model, modeladmin)) for c in cols])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="5B3A6E")
    for obj in queryset[:50000]:
        ws.append([_value(c, obj, modeladmin) for c in cols])
    for i, c in enumerate(cols, 1):
        width = max((len(str(ws.cell(row=r, column=i).value or "")) for r in range(1, min(ws.max_row, 200) + 1)), default=10)
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 60)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    name = slugify(str(model._meta.verbose_name_plural).replace("ı", "i")) or "liste"
    resp["Content-Disposition"] = f'attachment; filename="{name}-{timezone.localdate():%Y%m%d}.xlsx"'
    wb.save(resp)
    return resp


def export_selected(modeladmin, request, queryset):
    return xlsx_response(modeladmin, request, queryset)


export_selected.short_description = "Seçilenleri Excel'e aktar"
