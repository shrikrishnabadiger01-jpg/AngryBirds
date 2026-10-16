"""Small local account/session layer for production deployments.

APP_USERS_JSON maps usernames to PBKDF2 password hashes and one of admin,
operator, or auditor roles. Create hashes with ``py -m app.auth --hash``.
"""
import base64
import hashlib
import hmac
import json
import secrets
import sys
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])
COOKIE_NAME = "app_session"
SESSION_SECONDS = 8 * 60 * 60
ROLES = {"admin", "operator", "auditor"}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$", 3)
        rounds = int(rounds)
        if scheme != "pbkdf2_sha256" or not 100_000 <= rounds <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), rounds)
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def _valid_password_hash(encoded: str) -> bool:
    try:
        scheme, rounds, salt, digest = encoded.split("$", 3)
        return scheme == "pbkdf2_sha256" and 100_000 <= int(rounds) <= 1_000_000 and len(_unb64(salt)) >= 16 and len(_unb64(digest)) == 32
    except (ValueError, TypeError):
        return False


def load_users():
    try:
        users = json.loads(settings.auth_users_json or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("APP_USERS_JSON must be valid JSON") from exc
    if not isinstance(users, dict):
        raise RuntimeError("APP_USERS_JSON must be a username-to-account object")
    for username, account in users.items():
        if not isinstance(account, dict) or account.get("role") not in ROLES:
            raise RuntimeError(f"Invalid role configuration for user {username!r}")
        if not _valid_password_hash(account.get("password_hash", "")):
            raise RuntimeError(f"Invalid PBKDF2 password hash for user {username!r}")
    return users


def read_session(token: str | None):
    if not token or not settings.secret_key:
        return None
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) <= int(time.time()) or payload.get("role") not in ROLES:
            return None
        account = load_users().get(payload.get("username"))
        if (
            not account
            or account.get("role") != payload["role"]
            or not hmac.compare_digest(
                payload.get("credential_version", ""),
                hashlib.sha256(account["password_hash"].encode()).hexdigest(),
            )
        ):
            return None
        return {"username": payload["username"], "role": payload["role"]}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _make_session(username: str, account: dict):
    payload = {
        "username": username,
        "role": account["role"],
        "credential_version": hashlib.sha256(account["password_hash"].encode()).hexdigest(),
        "exp": int(time.time()) + SESSION_SECONDS,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)


@router.get("/session")
def get_session(request: Request):
    user = getattr(request.state, "user", None)
    return {"required": settings.auth_enabled, "user": user if settings.auth_enabled else None}


@router.post("/login")
def login(req: LoginRequest, response: Response):
    users = load_users()
    account = users.get(req.username)
    encoded_hash = account.get("password_hash", "") if account else hash_password("invalid-user")
    valid = _verify_password(req.password, encoded_hash)
    if not account or not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _make_session(req.username, account)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        path="/",
    )
    return {"username": req.username, "role": account["role"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=settings.app_env.lower() == "production", samesite="strict")
    return {"logged_out": True}


def require_roles(*allowed_roles):
    def dependency(request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role for this action")
        return user
    return Depends(dependency)


@router.get("/users", dependencies=[require_roles("admin")])
def list_users():
    """Return account names and roles without exposing hashes or credentials."""
    return [{"username": username, "role": account["role"]} for username, account in sorted(load_users().items())]


if __name__ == "__main__" and "--hash" in sys.argv:
    print(hash_password(sys.argv[sys.argv.index("--hash") + 1]))
