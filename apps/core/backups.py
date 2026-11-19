"""
Yedek al / geri dön / taşı. Bir yedek = tek .zip:
  meta.json  : ad, tarih, alan kişi, tür, modüller, kayıt sayıları, şifre anahtarı parmak izi
  data.json  : tüm veritabanı (Django dumpdata; PostgreSQL ve SQLite arasında taşınabilir)
  media/...  : ürün fotoğrafları
Geri dönüş tek işlemde yapılır (veritabanı boşaltılır + yedek yüklenir; hata olursa hiçbir şey değişmez),
ardından fotoğraflar değiştirilir. Geri dönmeden önce otomatik bir yedek alınır.
Yeni sunucuya taşıma: `python manage.py restore_backup dosya.zip` (bkz. docs/DEPLOY.md).
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from apps.core.events import publish

EXCLUDE = ["sessions", "contenttypes", "auth.permission", "admin.logentry"]
NAME_RE = re.compile(r"^[\w\-]+\.zip$")


def root():
    p = Path(settings.BACKUP_ROOT)
    p.mkdir(parents=True, exist_ok=True)
    return p


def key_fingerprint():
    """Entegrasyon şifrelerini açan anahtarın parmak izi (anahtarın kendisi yazılmaz)."""
    return hashlib.sha256(("erp-integrations:" + settings.SECRET_KEY).encode()).hexdigest()[:12]


def _slug(text):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ ", "cgiosuCGIOSU-")
    return re.sub(r"[^\w\-]", "", (text or "yedek").translate(tr))[:40] or "yedek"


def _path(filename):
    if not NAME_RE.match(filename or ""):
        raise ValidationError("Geçersiz yedek adı.")
    p = root() / filename
    if not p.exists():
        raise ValidationError("Yedek bulunamadı.")
    return p


def create_backup(name, user=None, kind="manual"):
    """Yedek alır. kind: manual | auto | upload. Döner: dosya adı."""
    from apps.core.registry import load_manifests
    stamp = timezone.localtime()
    filename = f"{stamp:%Y%m%d-%H%M%S}-{_slug(name)}.zip"
    media = Path(settings.MEDIA_ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data.json"
        from django.apps import apps
        unmanaged = [m._meta.label for m in apps.get_models() if not m._meta.managed]  # yalnız izin taşıyan modeller
        call_command("dumpdata", exclude=EXCLUDE + unmanaged, natural_foreign=True, output=str(data), verbosity=0)
        with data.open(encoding="utf-8") as fh:
            rows = json.load(fh)
        counts = {}
        for r in rows:
            counts[r["model"]] = counts.get(r["model"], 0) + 1
        meta = {"name": name or "Yedek", "created_at": stamp.isoformat(), "created_by": str(user or "sistem"), "kind": kind,
                "modules": list(load_manifests().keys()), "records": len(rows), "counts": counts,
                "key_fingerprint": key_fingerprint(), "format": 1}
        part = root() / (filename + ".part")
        with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=1))
            z.write(data, "data.json")
            if media.exists():
                for f in media.rglob("*"):
                    if f.is_file():
                        z.write(f, "media/" + f.relative_to(media).as_posix(), compress_type=zipfile.ZIP_STORED)
        part.rename(root() / filename)
    if kind == "auto":
        _prune_auto()
    return filename


def read_meta(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if not {"meta.json", "data.json"} <= names:
                raise ValidationError("Bu dosya bir Eglo ERP yedeği değil (meta.json / data.json yok).")
            meta = json.loads(z.read("meta.json").decode("utf-8"))
            meta["photos"] = sum(1 for n in names if n.startswith("media/") and not n.endswith("/"))
    except zipfile.BadZipFile:
        raise ValidationError("Dosya bozuk veya .zip değil.")
    meta["file"], meta["size"] = Path(path).name, Path(path).stat().st_size
    try:
        meta["created"] = dt.datetime.fromisoformat(meta["created_at"])
    except (KeyError, ValueError):
        meta["created"] = None
    meta["key_ok"] = meta.get("key_fingerprint") == key_fingerprint()
    return meta


def list_backups():
    out = []
    for p in sorted(root().glob("*.zip"), reverse=True):
        try:
            out.append(read_meta(p))
        except ValidationError:
            continue
    return out


def _prune_auto():
    autos = [b for b in list_backups() if b.get("kind") == "auto"]
    for b in autos[settings.BACKUP_KEEP_AUTO:]:
        (root() / b["file"]).unlink(missing_ok=True)


def delete_backup(filename):
    _path(filename).unlink()


def save_upload(upload):
    """Bilgisayardan yüklenen yedek dosyasını doğrulayıp listeye ekler."""
    if not (upload.name or "").lower().endswith(".zip"):
        raise ValidationError("Yedek dosyası .zip olmalı.")
    part = root() / f"upload-{timezone.now():%Y%m%d%H%M%S%f}.part"
    with part.open("wb") as fh:
        for chunk in upload.chunks():
            fh.write(chunk)
    try:
        meta = read_meta(part)
    except ValidationError:
        part.unlink(missing_ok=True)
        raise
    name = f"{timezone.localtime():%Y%m%d-%H%M%S}-yuklenen-{_slug(meta.get('name'))}.zip"
    part.rename(root() / name)
    return name


def _safe_member(name):
    p = Path(name)
    return name.startswith("media/") and not name.endswith("/") and not p.is_absolute() and ".." not in p.parts


@transaction.atomic
def _load_database(data_file):
    # Boşalt (izinler / içerik türleri bu sürümün kodundan yeniden oluşur) ve yedeği yükle.
    call_command("flush", interactive=False, verbosity=0)
    call_command("loaddata", str(data_file), verbosity=0)


def restore_backup(filename=None, path=None, user=None, safety_backup=True):
    """
    Sistemi yedekteki ana döndürür (tüm modüller birlikte). Döner: {"safety": otomatik_yedek_adı, "warnings": [...]}
    Not: tüm oturumlar kapanır; herkes yeniden giriş yapar.
    """
    path = Path(path) if path else _path(filename)
    meta = read_meta(path)
    from apps.core.registry import load_manifests
    missing = [m for m in meta.get("modules", []) if m not in load_manifests()]
    if missing:
        raise ValidationError("Yedekte bu sunucuda kapalı modüller var: " + ", ".join(missing) + ". Önce modülleri açın.")
    safety = create_backup("Geri dönüş öncesi otomatik", user, kind="auto") if safety_backup else None
    media = Path(settings.MEDIA_ROOT)
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(path) as z:
        data = Path(tmp) / "data.json"
        data.write_bytes(z.read("data.json"))
        _load_database(data)
        # Fotoğraflar: önce geçici klasöre çıkar, sonra değiştir
        new_media = Path(tmp) / "media"
        new_media.mkdir()
        for n in z.namelist():
            if _safe_member(n):
                target = new_media / n[len("media/"):]
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        media.mkdir(parents=True, exist_ok=True)
        for child in media.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        for child in new_media.iterdir():
            shutil.move(str(child), str(media / child.name))
    warnings = []
    if not meta["key_ok"]:
        warnings.append("Bu yedek başka bir gizli anahtarla (DJANGO_SECRET_KEY) alınmış: entegrasyon şifreleri (Uyumsoft, Trendyol, "
                        "e-posta...) açılamaz. Eski sunucudaki .env dosyasındaki DJANGO_SECRET_KEY'i bu sunucuya kopyalayın "
                        "ya da Entegrasyonlar'dan şifreleri yeniden girin.")
    publish("core.restored", meta=meta)
    return {"safety": safety, "warnings": warnings, "meta": meta}


# ---------------------------------------------------------------- test verilerini temizle
def reset_groups():
    """Modüllerin MANIFEST['reset_data'] tanımları: [(anahtar, etiket, açıklama, modeller, numara serileri)]"""
    from apps.core.registry import load_manifests
    out = []
    for code, m in load_manifests().items():
        for i, g in enumerate(m.get("reset_data", [])):
            out.append({"key": f"{code}:{i}", "label": g["label"], "desc": g.get("desc", ""), "models": g["models"],
                        "sequences": g.get("sequences", []), "module": m["name"]})
    return out


def reset_test_data(keys, user=None):
    """
    Seçilen gruplardaki hareket verilerini siler; ana veriler (ürün, cari, depo, reçete, ayarlar, kullanıcılar) kalır.
    Önce otomatik yedek alınır. Başka bir grubun kaydı engel olursa hiçbir şey silinmez ve hangi grubun da seçilmesi gerektiği söylenir.
    """
    from django.apps import apps
    from django.db.models import ProtectedError, RestrictedError

    from apps.core.models import Sequence
    groups = [g for g in reset_groups() if g["key"] in set(keys)]
    if not groups:
        raise ValidationError("Temizlenecek grup seçin.")
    safety = create_backup("Temizlik öncesi otomatik", user, kind="auto")
    models = [apps.get_model(m) for g in groups for m in g["models"]]
    counts = {}
    try:
        with transaction.atomic():
            pending = list(models)
            while pending:
                progressed, blocked = False, []
                for M in pending:
                    try:
                        n = M.objects.all().delete()[0]
                        counts[M._meta.verbose_name_plural] = counts.get(M._meta.verbose_name_plural, 0) + n
                        progressed = True
                    except (ProtectedError, RestrictedError) as exc:
                        blocked.append((M, exc))
                if not progressed:
                    M, exc = blocked[0]
                    other = next(iter(exc.protected_objects if hasattr(exc, "protected_objects") else exc.restricted_objects))
                    raise ValidationError(f"'{M._meta.verbose_name_plural}' silinemiyor: '{other._meta.verbose_name_plural}' kayıtları "
                                          f"bunlara bağlı. İlgili grubu da seçin.")
                pending = [M for M, _ in blocked]
            for g in groups:
                for prefix in g["sequences"]:
                    Sequence.objects.filter(code__startswith=prefix).delete()
    except ValidationError:
        (root() / safety).unlink(missing_ok=True)
        raise
    publish("core.test_data_reset", groups=[g["key"] for g in groups])
    return {"safety": safety, "counts": counts}
