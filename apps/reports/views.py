import datetime as dt
from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .registry import REPORTS

PERM = "reports.view_report"


def _params(request):
    today = timezone.localdate()
    def d(key, default):
        try:
            return dt.date.fromisoformat(request.GET.get(key, ""))
        except ValueError:
            return default
    return {"start": d("start", today - dt.timedelta(days=89)), "end": d("end", today),
            "warehouse": request.GET.get("warehouse") or None, "channel": request.GET.get("channel") or None,
            "days": request.GET.get("days") or 180}


@login_required
@permission_required(PERM, raise_exception=True)
def index(request):
    return render(request, "reports/index.html", {"reports": REPORTS})


@login_required
@permission_required(PERM, raise_exception=True)
def show(request, code):
    rep = REPORTS.get(code)
    if rep is None:
        raise Http404
    p = _params(request)
    data = rep["fn"](p)
    if request.GET.get("format") == "xlsx":
        return _xlsx(rep["title"], p, data)
    from apps.catalog.models import SalesChannel
    from apps.inventory.models import Warehouse
    return render(request, "reports/show.html", {
        "code": code, "rep": rep, "p": p, "data": data, "warehouses": Warehouse.objects.all(),
        "channels": SalesChannel.objects.all(), "generated": timezone.localtime()})


def _xlsx(title, p, data):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = title[:30]
    ws.append([title])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([f"Dönem: {p['start']:%d.%m.%Y} – {p['end']:%d.%m.%Y} · Oluşturma: {timezone.localtime():%d.%m.%Y %H:%M}"])
    ws.append([])
    ws.append([c[1] for c in data["columns"]])
    for cell in ws[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0F766E")
    fmt = {"money": "#,##0.00", "qty": "#,##0.###", "pct": "0.00", "int": "0"}
    for r in data["rows"]:
        ws.append([float(r.get(k)) if isinstance(r.get(k), Decimal) else r.get(k) for k, _, _ in data["columns"]])
        for i, (_, _, kind) in enumerate(data["columns"], start=1):
            if kind in fmt:
                ws.cell(row=ws.max_row, column=i).number_format = fmt[kind]
    if data.get("totals"):
        ws.append([("Toplam" if i == 0 else (float(data["totals"][k]) if k in data["totals"] else None))
                   for i, (k, _, _) in enumerate(data["columns"])])
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)
    for i, (_, label, kind) in enumerate(data["columns"], start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(40, len(label) + 4 if kind != "text" else 28))
    ws.freeze_panes = "A5"
    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    name = title.replace(" ", "_").replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    resp["Content-Disposition"] = f'attachment; filename="{name}_{timezone.localdate():%Y%m%d}.xlsx"'
    wb.save(resp)
    return resp
