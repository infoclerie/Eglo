from decimal import Decimal

from .models import Product


def update_average_cost(product, on_hand_qty, incoming_qty, incoming_unit_cost):
    """
    Ağırlıklı ortalama maliyet:
        yeni maliyet = (eldeki miktar × eski maliyet + gelen miktar × gelen birim maliyet) / (eldeki + gelen)
    Eldeki miktar 0 veya negatifse yeni maliyet = gelen birim maliyet.
    """
    on_hand, qty, cost = Decimal(str(on_hand_qty)), Decimal(str(incoming_qty)), Decimal(str(incoming_unit_cost))
    if qty <= 0:
        return product.cost
    if on_hand <= 0:
        new = cost
    else:
        new = (on_hand * product.cost + qty * cost) / (on_hand + qty)
    new = new.quantize(Decimal("0.01"))
    Product.objects.filter(pk=product.pk).update(cost=new)
    product.cost = new
    return new


def find_product(code):
    """SKU, ürün barkodu veya koli barkodu ile ürün bulur. Döner: (ürün, çarpan) — koli barkodunda çarpan = koli içi adet."""
    p = Product.objects.filter(barcode=code).first() or Product.objects.filter(sku=code).first()
    if p:
        return p, 1
    p = Product.objects.filter(case_barcode=code).first()
    return (p, p.units_per_case) if p else (None, 0)


# ---------------------------------------------------------------- ürün fotoğrafları
MAX_SIDE, THUMB_SIDE = 1600, 360
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "MPO", "GIF"}


def _jpeg(img, side):
    from io import BytesIO

    from PIL import Image
    im = img.copy()
    im.thumbnail((side, side), Image.LANCZOS)
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        im = bg
    buf = BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return buf.getvalue()


def add_image(product, upload, user=None, note="", make_main=False):
    """
    Fotoğrafı doğrular, telefonun yön bilgisine göre döndürür, en fazla 1600 px JPEG'e küçültür (+360 px önizleme) ve kaydeder.
    Ürünün ilk fotoğrafı otomatik ana görsel olur.
    """
    import uuid

    from django.core.exceptions import ValidationError
    from django.core.files.base import ContentFile
    from PIL import Image, ImageOps, UnidentifiedImageError

    from .models import ProductImage
    if upload.size > 25 * 1024 * 1024:
        raise ValidationError("Fotoğraf 25 MB'dan büyük olamaz.")
    try:
        img = Image.open(upload)
        fmt = img.format
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError):
        raise ValidationError(f"'{getattr(upload, 'name', 'dosya')}' bir fotoğraf değil (JPG, PNG, WEBP yükleyin).")
    if fmt not in ALLOWED_FORMATS:
        raise ValidationError(f"Desteklenmeyen görsel türü: {fmt}")
    name = f"{product.sku}-{uuid.uuid4().hex[:8]}.jpg".replace("/", "-")
    first = not product.images.exists()
    pi = ProductImage(product=product, uploaded_by=user, note=note[:150], is_main=first or make_main)
    pi.image.save(name, ContentFile(_jpeg(img, MAX_SIDE)), save=False)
    pi.thumb.save(name, ContentFile(_jpeg(img, THUMB_SIDE)), save=False)
    pi.save()
    if pi.is_main and not first:
        product.images.exclude(pk=pi.pk).update(is_main=False)
    return pi


def set_main_image(image):
    image.product.images.exclude(pk=image.pk).update(is_main=False)
    image.is_main = True
    image.save(update_fields=["is_main"])


def delete_image(image):
    product, was_main = image.product, image.is_main
    files = [f for f in (image.image, image.thumb) if f]
    storage, names = (files[0].storage if files else None), [f.name for f in files]
    image.delete()
    for n in names:
        storage.delete(n)
    if was_main:
        nxt = product.images.order_by("-created_at").first()
        if nxt:
            set_main_image(nxt)
