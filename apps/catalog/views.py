from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Product


def save_photos(request, product, note=""):
    """Formdaki 'photos' dosyalarını ürüne ekler; hataları mesaj olarak gösterir. Döner: eklenen adet."""
    n = 0
    for f in request.FILES.getlist("photos"):
        try:
            services.add_image(product, f, request.user, note)
            n += 1
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    return n


@login_required
@permission_required("catalog.view_product", raise_exception=True)
def photos(request, pk):
    p = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        if not request.user.has_perm("catalog.add_productimage"):
            messages.error(request, "Fotoğraf yükleme yetkiniz yok.")
        elif request.POST.get("main"):
            services.set_main_image(get_object_or_404(p.images, pk=request.POST["main"]))
            messages.success(request, "Ana görsel değiştirildi.")
        elif request.POST.get("delete"):
            services.delete_image(get_object_or_404(p.images, pk=request.POST["delete"]))
            messages.success(request, "Fotoğraf silindi.")
        else:
            n = save_photos(request, p, request.POST.get("note", ""))
            if n:
                messages.success(request, f"{n} fotoğraf yüklendi.")
        return redirect(request.POST.get("next") or request.path)
    return render(request, "catalog/photos.html", {"p": p, "images": p.images.all()})
