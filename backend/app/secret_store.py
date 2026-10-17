"""Encrypt sensitive Gmail credential fields when a stable secret key is configured."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

PREFIX = "enc:v1:"


def is_protected(value: str | None):
    return value is None or value.startswith(PREFIX)


def _fernet():
    if not settings.secret_key:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def protect(value: str | None):
    if value is None or not settings.secret_key or value.startswith(PREFIX):
        return value
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def reveal(value: str | None):
    if value is None or not value.startswith(PREFIX):
        return value
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError("SECRET_KEY is required to decrypt stored Gmail credentials")
    try:
        return fernet.decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt Gmail credentials; verify SECRET_KEY") from exc
