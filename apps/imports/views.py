import base64
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from . import services

PERM = "imports.add_importpermission"
MAX_BYTES = 8 * 1024 * 1024


@login_required
@permission_required(PERM, raise_exception=True)
def index(request):
    return render(request, "imports/index.html", {"kinds": services.KINDS})


@login_required
@permission_required(PERM, raise_exception=True)
def template(request, kind):
    if kind not in services.KINDS:
        raise Http404
    resp = HttpResponse(services.template_xlsx(kind), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="eglo_sablon_{kind}.xlsx"'
    return resp


@login_required
@permission_required(PERM, raise_exception=True)
def upload(request, kind):
    if kind not in services.KINDS:
        raise Http404
    meta = services.KINDS[kind]
    key = f"import_{kind}"
    rows, error = None, None
    if request.method == "POST" and request.POST.get("confirm") and request.session.get(key):
        try:
            rows = services.parse(kind, BytesIO(base64.b64decode(request.session[key])))
            counts = services.apply(kind, rows, request.user)
            del request.session[key]
            messages.success(request, f"{meta['title']}: {counts['created']} yeni, {counts['updated']} güncellenen kayıt.")
            return redirect("imports:index")
        except ValidationError as exc:
            error = " ".join(exc.messages)
    elif request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        if f.size > MAX_BYTES:
            error = "Dosya 8 MB'dan büyük olamaz."
        else:
            raw = f.read()
            try:
                rows = services.parse(kind, BytesIO(raw))
                request.session[key] = base64.b64encode(raw).decode()
            except ValidationError as exc:
                error = " ".join(exc.messages)
    cols = meta["cols"]()
    bad = sum(1 for r in rows or [] if r["errors"])
    return render(request, "imports/upload.html", {"kind": kind, "meta": meta, "rows": rows, "error": error, "cols": cols,
                                                    "bad": bad, "good": len(rows or []) - bad})
