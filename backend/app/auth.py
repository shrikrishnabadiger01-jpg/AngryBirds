"""Small local account/session layer for production deployments.

APP_USERS_JSON maps usernames to PBKDF2 password hashes and one of admin,
operator, or auditor roles. Create hashes with ``py -m app.auth --hash``.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import sys
import time

import httpx
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
        if settings.auth_mode == "minimoth_otp":
            header, body, signature = token.split(".", 2)
            signed = f"{header}.{body}"
            expected = _b64(hmac.new(settings.secret_key.encode(), signed.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(expected, signature):
                return None
            jwt_header = json.loads(_unb64(header))
            payload = json.loads(_unb64(body))
            if jwt_header.get("alg") != "HS256" or jwt_header.get("typ") != "JWT":
                return None
            if payload.get("iss") != "ai-agent-security" or payload.get("exp", 0) <= int(time.time()) or payload.get("role") != settings.auth_default_role:
                return None
            phone = payload.get("sub", "")
            if not isinstance(phone, str) or not phone.startswith("+"):
                return None
            return {"username": phone, "role": payload["role"]}

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


def _make_otp_session(phone: str):
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({
        "iss": "ai-agent-security",
        "sub": phone,
        "role": settings.auth_default_role,
        "iat": now,
        "exp": now + SESSION_SECONDS,
    }, separators=(",", ":")).encode())
    signed = f"{header}.{payload}"
    signature = _b64(hmac.new(settings.secret_key.encode(), signed.encode(), hashlib.sha256).digest())
    return f"{signed}.{signature}"


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        path="/",
    )


def _normalize_phone(phone: str):
    compact = re.sub(r"[\s()-]", "", phone)
    if re.fullmatch(r"[6-9]\d{9}", compact):
        compact = f"+91{compact}"
    if not re.fullmatch(r"\+[1-9]\d{7,14}", compact):
        raise HTTPException(status_code=422, detail="Enter a valid phone number in international format, such as +919876543210.")
    return compact


async def _minimoth_request(path: str, payload: dict):
    if not settings.minimoth_api_key.strip():
        raise HTTPException(status_code=503, detail="MiniMoth authentication is not configured. Set MINIMOTH_API_KEY in backend/.env.")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"https://api.minimoth.dev/v1/{path}",
                headers={"X-Api-Key": settings.minimoth_api_key.strip(), "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach MiniMoth. Please try again.") from exc
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.is_success:
        code = data.get("code") if isinstance(data, dict) else None
        status = 503 if code == "INVALID_API_KEY" or response.status_code in (401, 403) else (
            429 if response.status_code == 429 or code in {"OTP_RATE_LIMITED", "VERIFY_RATE_LIMITED"} else
            422 if code in {"INVALID_PHONE", "INVALID_OTP_CODE"} else
            401 if code == "INVALID_OTP" else 410 if code == "OTP_NOT_FOUND" else
            402 if code == "INSUFFICIENT_BALANCE" else 502
        )
        message = {
            "INVALID_API_KEY": "MiniMoth rejected MINIMOTH_API_KEY. Check the key in your MiniMoth dashboard.",
            "OTP_RATE_LIMITED": "Too many OTP requests. Wait before trying again.",
            "INVALID_OTP": "The code is incorrect. Check it and try again.",
            "OTP_NOT_FOUND": "That code expired or was already used. Request a new code.",
            "VERIFY_RATE_LIMITED": "Too many incorrect codes. Request a new code and try again.",
            "INVALID_PHONE": "Enter a supported phone number in international format.",
            "INVALID_OTP_CODE": "Enter the 6-digit verification code.",
            "INSUFFICIENT_BALANCE": "MiniMoth has insufficient balance to send this OTP.",
        }.get(code, "MiniMoth could not complete the OTP request.")
        raise HTTPException(status_code=status, detail=message)
    return data


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)


class PhoneRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=24)


class OTPVerifyRequest(PhoneRequest):
    code: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")


@router.get("/session")
def get_session(request: Request):
    user = getattr(request.state, "user", None)
    return {"required": settings.auth_enabled, "mode": settings.auth_mode, "user": user if settings.auth_enabled else None}


@router.post("/otp/send")
async def send_login_otp(req: PhoneRequest):
    if not settings.auth_enabled or settings.auth_mode != "minimoth_otp":
        raise HTTPException(status_code=404, detail="MiniMoth OTP login is not enabled.")
    phone = _normalize_phone(req.phone)
    data = await _minimoth_request("otp/send", {"phone": phone})
    return {"sent": True, "phone": phone, "otp_id": data.get("otp_id"), "expires_at": data.get("expires_at")}


@router.post("/otp/verify")
async def verify_login_otp(req: OTPVerifyRequest, response: Response):
    if not settings.auth_enabled or settings.auth_mode != "minimoth_otp":
        raise HTTPException(status_code=404, detail="MiniMoth OTP login is not enabled.")
    phone = _normalize_phone(req.phone)
    await _minimoth_request("otp/verify", {"phone": phone, "code": req.code})
    user = {"username": phone, "role": settings.auth_default_role}
    _set_session_cookie(response, _make_otp_session(phone))
    return user


@router.post("/login")
def login(req: LoginRequest, response: Response):
    if settings.auth_mode != "password":
        raise HTTPException(status_code=404, detail="Password login is not enabled.")
    users = load_users()
    account = users.get(req.username)
    encoded_hash = account.get("password_hash", "") if account else hash_password("invalid-user")
    valid = _verify_password(req.password, encoded_hash)
    if not account or not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _make_session(req.username, account)
    _set_session_cookie(response, token)
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
