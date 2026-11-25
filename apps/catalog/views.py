from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Brand, Category, KitComponent, Product, ProductPrice, SalesChannel


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
def product_list(request):
    """Ürün kartları listesi — arama, filtre, ana görsel."""
    qs = Product.objects.select_related("brand", "category").prefetch_related("images").order_by("sku")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q) | Q(barcode=q) | Q(case_barcode=q))
    kind = request.GET.get("kind")
    if kind:
        qs = qs.filter(kind=kind)
    brand = request.GET.get("brand")
    if brand:
        qs = qs.filter(brand_id=brand)
    cat = request.GET.get("category")
    if cat:
        qs = qs.filter(category_id=cat)
    active = request.GET.get("active", "1")
    if active == "1":
        qs = qs.filter(active=True)
    elif active == "0":
        qs = qs.filter(active=False)
    return render(request, "catalog/product_list.html", {
        "products": qs[:500],
        "q": q,
        "brands": Brand.objects.order_by("name"),
        "categories": Category.objects.select_related("parent").order_by("parent__name", "name"),
        "kinds": Product.KIND,
        "filters": {"kind": kind or "", "brand": brand or "", "category": cat or "", "active": active},
    })


@login_required
@permission_required("catalog.view_product", raise_exception=True)
def product_detail(request, pk):
    """Ürün detay: bilgiler, set bileşenleri, fotoğraflar, fiyatlar."""
    p = get_object_or_404(Product.objects.select_related("brand", "category"), pk=pk)
    return render(request, "catalog/product_detail.html", {
        "p": p,
        "images": p.images.all(),
        "components": p.components.select_related("component") if p.is_kit else [],
        "prices": p.prices.select_related("channel"),
        "stock": _safe_stock(p),
    })


def _safe_stock(product):
    try:
        from apps.inventory.services import stock_summary
        return stock_summary(product)
    except Exception:
        return {}


@login_required
@permission_required("catalog.add_product", raise_exception=True)
def product_create(request):
    """Yeni ürün oluşturma (fotoğraf yükleme dahil)."""
    if request.method == "POST":
        try:
            p = _save_product_form(request)
            # Fotoğraf yükleme
            n = save_photos(request, p)
            msg = f"Ürün oluşturuldu: {p}"
            if n:
                msg += f" · {n} fotoğraf eklendi"
            messages.success(request, msg)
            return redirect("catalog:detail", pk=p.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages) if hasattr(exc, 'messages') else str(exc))

    return render(request, "catalog/product_form.html", {
        "title": "Yeni Ürün",
        "brands": Brand.objects.order_by("name"),
        "categories": Category.objects.select_related("parent").order_by("parent__name", "name"),
        "channels": SalesChannel.objects.filter(active=True),
        "kinds": Product.KIND,
        "units": Product.UNIT,
        "groups": Product.GROUP,
    })


@login_required
@permission_required("catalog.change_product", raise_exception=True)
def product_edit(request, pk):
    """Ürün düzenleme."""
    p = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            _save_product_form(request, p)
            n = save_photos(request, p)
            msg = f"Ürün güncellendi: {p}"
            if n:
                msg += f" · {n} fotoğraf eklendi"
            messages.success(request, msg)
            return redirect("catalog:detail", pk=p.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages) if hasattr(exc, 'messages') else str(exc))

    return render(request, "catalog/product_form.html", {
        "title": f"Düzenle: {p.sku}",
        "p": p,
        "brands": Brand.objects.order_by("name"),
        "categories": Category.objects.select_related("parent").order_by("parent__name", "name"),
        "channels": SalesChannel.objects.filter(active=True),
        "kinds": Product.KIND,
        "units": Product.UNIT,
        "groups": Product.GROUP,
        "prices": {pp.channel_id: pp.price for pp in p.prices.all()},
    })


def _save_product_form(request, product=None):
    """POST verisinden ürün oluştur/güncelle."""
    d = request.POST
    is_new = product is None
    if is_new:
        product = Product()
    product.sku = d.get("sku", product.sku if not is_new else "").strip()
    product.barcode = d.get("barcode", "").strip() or None
    product.name = d.get("name", "").strip()
    product.kind = d.get("kind", "standard")
    product.unit = d.get("unit", "pcs")
    product.group = d.get("group", "other")
    product.description = d.get("description", "")
    product.volume = d.get("volume", "")
    product.brand_id = d.get("brand") or None
    product.category_id = d.get("category") or None
    product.case_barcode = d.get("case_barcode", "").strip() or None
    from decimal import Decimal, InvalidOperation
    for f in ("weight_kg", "units_per_case", "cases_per_pallet", "cost", "list_price", "vat_rate",
              "min_stock", "max_stock", "safety_stock", "lead_time_days", "shelf_life_days"):
        val = d.get(f, "").strip()
        if val:
            try:
                if f in ("units_per_case", "cases_per_pallet", "lead_time_days", "shelf_life_days"):
                    setattr(product, f, int(val))
                else:
                    setattr(product, f, Decimal(val))
            except (InvalidOperation, ValueError):
                pass
    product.track_lot = d.get("track_lot") == "on"
    product.storage_condition = d.get("storage_condition", "")
    product.active = d.get("active", "on") == "on"
    product.full_clean()
    product.save()

    # Kanal fiyatları
    for ch in SalesChannel.objects.filter(active=True):
        price_val = d.get(f"price_{ch.pk}", "").strip()
        if price_val:
            try:
                ProductPrice.objects.update_or_create(product=product, channel=ch,
                                                      defaults={"price": Decimal(price_val)})
            except (InvalidOperation, ValueError):
                pass
        else:
            ProductPrice.objects.filter(product=product, channel=ch).delete()

    # Set bileşenleri (kind=kit ise)
    if product.kind == "kit":
        existing = set(product.components.values_list("pk", flat=True))
        kept = set()
        idx = 0
        while True:
            comp_id = d.get(f"comp_product_{idx}")
            comp_qty = d.get(f"comp_qty_{idx}", "1")
            if comp_id is None and idx > 20:
                break
            if comp_id:
                try:
                    kc, _ = KitComponent.objects.update_or_create(
                        kit=product, component_id=int(comp_id),
                        defaults={"quantity": Decimal(comp_qty)})
                    kept.add(kc.pk)
                except (ValueError, InvalidOperation, ValidationError):
                    pass
            idx += 1
        product.components.exclude(pk__in=kept).delete()
    return product


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


@login_required
def subcategories(request):
    """AJAX: Üst kategoriye göre alt kategorileri döndürür."""
    parent_id = request.GET.get("parent")
    if parent_id:
        cats = Category.objects.filter(parent_id=parent_id).values("id", "name")
    else:
        cats = Category.objects.filter(parent__isnull=True).values("id", "name")
    return JsonResponse(list(cats), safe=False)
