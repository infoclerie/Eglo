"""
Kod güncelleme sistemi (SSH gerektirmez).

Akış:
  1. AI, değişen dosyaları içeren bir güncelleme paketi (zip) üretir.
  2. Kullanıcı Sistem › Güncellemeler sayfasından zip'i yükler.
  3. Zip, Docker paylaşımlı volumes/updates/pending/ dizinine kaydedilir.
  4. Host'taki cron betiği (deploy/auto-update.sh) yeni zip'i algılar:
     - Dosyaları proje dizinine çıkarır
     - docker compose up -d --build çalıştırır
     - Sonucu updates/status.json'a yazar
  5. Web arayüzü status.json'dan son durumu gösterir.

Güncelleme zip yapısı:
  meta.json       — sürüm, açıklama, dosya listesi, yönergeler
  files/          — değişen dosyalar (tam yol korunur)
    apps/catalog/views.py
    templates/base.html
    ...
"""
import json
import os
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

UPDATES_ROOT = Path(getattr(settings, "UPDATES_ROOT", Path(settings.BASE_DIR) / "updates"))


def _ensure_dirs():
    try:
        for sub in ("pending", "applied", "rejected"):
            (UPDATES_ROOT / sub).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Docker volume henüz mount edilmemiş olabilir


def pending_dir():
    _ensure_dirs()
    return UPDATES_ROOT / "pending"


def applied_dir():
    _ensure_dirs()
    return UPDATES_ROOT / "applied"


def status_file():
    return UPDATES_ROOT / "status.json"


def current_version():
    """Mevcut sürüm: status.json'dan veya PROJE_REHBERI_AI.md'den."""
    sf = status_file()
    if sf.exists():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            return data.get("current_version", "1.0.0")
        except (json.JSONDecodeError, OSError):
            pass
    return "1.0.0"


def read_update_meta(path):
    """Güncelleme zip'inin meta bilgilerini okur."""
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "meta.json" not in names:
                raise ValidationError("Bu dosya bir Eglo ERP güncelleme paketi değil (meta.json yok).")
            meta = json.loads(z.read("meta.json").decode("utf-8"))
            file_count = sum(1 for n in names if n.startswith("files/") and not n.endswith("/"))
            meta["file_count"] = file_count
            meta["files"] = sorted(n[6:] for n in names if n.startswith("files/") and not n.endswith("/"))
    except zipfile.BadZipFile:
        raise ValidationError("Dosya bozuk veya .zip değil.")
    meta["filename"] = path.name
    meta["size"] = path.stat().st_size
    return meta


def save_update(upload):
    """Kullanıcının yüklediği güncelleme zip'ini doğrulayıp pending/ dizinine kaydeder."""
    if not (upload.name or "").lower().endswith(".zip"):
        raise ValidationError("Güncelleme dosyası .zip olmalı.")

    _ensure_dirs()
    temp = pending_dir() / f"upload-{timezone.now():%Y%m%d%H%M%S%f}.part"
    with temp.open("wb") as fh:
        for chunk in upload.chunks():
            fh.write(chunk)

    try:
        meta = read_update_meta(temp)
    except ValidationError:
        temp.unlink(missing_ok=True)
        raise

    version = meta.get("version", "unknown")
    name = re.sub(r"[^a-z0-9._-]", "", f"update-v{version}".lower()) + ".zip"

    # Aynı sürüm zaten pending'de varsa üzerine yaz
    target = pending_dir() / name
    temp.rename(target)

    return meta


def list_pending():
    """Bekleyen (henüz uygulanmamış) güncellemeleri listeler."""
    _ensure_dirs()
    out = []
    for p in sorted(pending_dir().glob("*.zip"), reverse=True):
        try:
            out.append(read_update_meta(p))
        except (ValidationError, OSError):
            continue
    return out


def list_applied():
    """Daha önce uygulanmış güncellemeleri listeler."""
    _ensure_dirs()
    out = []
    for p in sorted(applied_dir().glob("*.zip"), reverse=True):
        try:
            out.append(read_update_meta(p))
        except (ValidationError, OSError):
            continue
    return out


def last_status():
    """Son güncelleme durumunu okur."""
    sf = status_file()
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def cancel_pending(filename):
    """Bekleyen bir güncellemeyi iptal eder (siler)."""
    if not re.match(r"^[\w\-\.]+\.zip$", filename or ""):
        raise ValidationError("Geçersiz dosya adı.")
    path = pending_dir() / filename
    if not path.exists():
        raise ValidationError("Güncelleme bulunamadı.")
    path.unlink()
