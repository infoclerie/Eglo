"""Entegrasyon şifrelerini veritabanında şifreli tutar. Anahtar: DJANGO_SECRET_KEY'den türetilir.
SECRET_KEY değişirse kayıtlı şifreler çözülemez → sihirbazdan şifreler yeniden girilmelidir."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    key = hashlib.sha256(("erp-integrations:" + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(text):
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return "{}"
