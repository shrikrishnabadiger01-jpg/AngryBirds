"""
IgnisGuard — Gmail Service
Handles Gmail API integration with Google OAuth 2.0.
Uses Gmail read and send scopes; outbound messages require explicit app approval.
Credentials and tokens are stored securely server-side in the SQLite database.
Never exposes OAuth secrets or access tokens to the frontend.
"""

import json
import secrets
import datetime
import base64
import html
import re
from email.message import EmailMessage
from typing import Optional, Dict, Any, List, Tuple

import httpx
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.database import SessionLocal, UserCredential
from app.secret_store import is_protected, protect, reveal


def get_stored_credentials() -> Tuple[Optional[Credentials], Optional[str]]:
    """
    Load credentials from SQLite database.
    Automatically refreshes expired tokens using the refresh token and persists the new token.
    """
    db = SessionLocal()
    try:
        user_cred = db.query(UserCredential).first()
        if not user_cred:
            return None, None

        scopes = json.loads(user_cred.scopes) if user_cred.scopes else settings.gmail_scopes

        try:
            creds = Credentials(
                token=reveal(user_cred.token),
                refresh_token=reveal(user_cred.refresh_token),
                token_uri=user_cred.token_uri,
                client_id=user_cred.client_id,
                client_secret=reveal(user_cred.client_secret),
                scopes=scopes,
                expiry=user_cred.expiry,
            )
        except RuntimeError as exc:
            # A SECRET_KEY change makes old encrypted tokens unusable. Treat the
            # connection as disconnected so health/status endpoints stay usable
            # and a fresh OAuth flow can replace the stale database record.
            print(f"[IgnisGuard] Stored Gmail credentials cannot be decrypted: {exc}")
            return None, None

        # Upgrade existing plaintext records on first access after production encryption is enabled.
        if settings.secret_key and any(not is_protected(value) for value in (user_cred.token, user_cred.refresh_token, user_cred.client_secret)):
            user_cred.token = protect(user_cred.token)
            user_cred.refresh_token = protect(user_cred.refresh_token)
            user_cred.client_secret = protect(user_cred.client_secret)
            db.commit()

        # If expired, attempt token refresh
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Update DB with fresh token and expiry
                user_cred.token = protect(creds.token)
                user_cred.expiry = creds.expiry
                user_cred.updated_at = datetime.datetime.utcnow()
                db.commit()
            except Exception as refresh_err:
                print(f"[IgnisGuard] Failed to refresh token: {refresh_err}")
                # If refresh fails and token is invalid, we return None
                if not creds.valid:
                    return None, None

        return creds, user_cred.email
    finally:
        db.close()


def save_credentials(creds: Credentials, email: str) -> None:
    """Save or update OAuth credentials in SQLite."""
    db = SessionLocal()
    try:
        user_cred = db.query(UserCredential).filter(UserCredential.email == email).first()
        if not user_cred:
            # Check if there's any existing record (single-user demo deployment)
            user_cred = db.query(UserCredential).first()

        scopes_json = json.dumps(list(creds.scopes)) if creds.scopes else json.dumps(settings.gmail_scopes)

        if user_cred:
            user_cred.email = email
            user_cred.token = protect(creds.token)
            if creds.refresh_token:
                user_cred.refresh_token = protect(creds.refresh_token)
            user_cred.token_uri = creds.token_uri or "https://oauth2.googleapis.com/token"
            user_cred.client_id = creds.client_id or settings.google_client_id
            user_cred.client_secret = protect(creds.client_secret or settings.google_client_secret)
            user_cred.scopes = scopes_json
            user_cred.expiry = creds.expiry
            user_cred.updated_at = datetime.datetime.utcnow()
        else:
            user_cred = UserCredential(
                email=email,
                token=protect(creds.token),
                refresh_token=protect(creds.refresh_token),
                token_uri=creds.token_uri or "https://oauth2.googleapis.com/token",
                client_id=creds.client_id or settings.google_client_id,
                client_secret=protect(creds.client_secret or settings.google_client_secret),
                scopes=scopes_json,
                expiry=creds.expiry,
            )
            db.add(user_cred)

        db.commit()
    finally:
        db.close()


def delete_credentials() -> bool:
    """Delete credentials from DB and revoke token with Google."""
    creds, _ = get_stored_credentials()
    if creds and creds.token:
        try:
            # Revoke token with Google
            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": creds.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
        except Exception as e:
            print(f"[IgnisGuard] Notice during token revocation: {e}")

    db = SessionLocal()
    try:
        deleted = db.query(UserCredential).delete()
        db.commit()
        return deleted > 0
    finally:
        db.close()


def create_oauth_flow() -> Tuple[Flow, str]:
    """Create a Google OAuth flow with configured Gmail scopes and secure CSRF state."""
    if not settings.has_google_credentials:
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env"
        )

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=settings.gmail_scopes,
        redirect_uri=settings.google_redirect_uri,
    )

    state = secrets.token_urlsafe(32)
    return flow, state


def get_auth_url() -> Tuple[str, str, str]:
    """Generate the Google OAuth consent URL."""
    flow, state = create_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url, state, flow.code_verifier


def handle_oauth_callback(code: str, state: str, code_verifier: str) -> Dict[str, Any]:
    """Exchange authorization code for tokens and persist server-side."""
    flow, _ = create_oauth_flow()
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Read authenticated user profile
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email_address = profile.get("emailAddress", "authorized_user")

    save_credentials(creds, email_address)

    return {
        "connected": True,
        "email": email_address,
        "scopes": list(creds.scopes) if creds.scopes else settings.gmail_scopes,
    }


def get_connection_status() -> Dict[str, Any]:
    """Return the current connection state without exposing secrets."""
    creds, email = get_stored_credentials()
    if creds and creds.valid:
        granted_scopes = list(creds.scopes or settings.gmail_scopes)
        return {
            "connected": True,
            "email": email,
            "configured": True,
            "scopes": granted_scopes,
            "can_send": "https://www.googleapis.com/auth/gmail.send" in granted_scopes,
        }
    return {
        "connected": False,
        "email": None,
        "configured": settings.has_google_credentials,
        "scopes": settings.gmail_scopes,
        "can_send": False,
    }


def has_scope(scope: str) -> bool:
    creds, _ = get_stored_credentials()
    return bool(creds and creds.valid and scope in (creds.scopes or []))


def send_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Send one message through Gmail using an explicitly granted send scope."""
    creds, connected_email = get_stored_credentials()
    if not creds or not creds.valid:
        raise PermissionError("Gmail is not connected. Connect Gmail before sending.")
    if "https://www.googleapis.com/auth/gmail.send" not in (creds.scopes or []):
        raise PermissionError("Gmail send access has not been granted. Reconnect Gmail and approve the send permission.")

    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    service = build("gmail", "v1", credentials=creds)
    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status == 401:
            raise PermissionError("Gmail authorization expired. Reconnect Gmail and try again.") from exc
        if status == 403:
            raise PermissionError("Google denied Gmail send access. Check the OAuth consent configuration.") from exc
        raise RuntimeError("Gmail could not send this message. Review the Gmail connection and try again.") from exc

    return {
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "sender": connected_email,
    }


def fetch_emails(
    max_results: int = 15,
    page_token: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch real messages from the authorized user's Gmail inbox.
    Decodes MIME multipart, extracts headers, sanitizes HTML, and never executes instructions.

    Returns:
        Dict with 'emails', 'next_page_token', and 'result_size_estimate'
    """
    creds, connected_email = get_stored_credentials()
    if not creds or not creds.valid:
        raise PermissionError("Gmail is not connected or token has expired. Please authenticate via OAuth.")

    service = build("gmail", "v1", credentials=creds)

    list_kwargs: Dict[str, Any] = {
        "userId": "me",
        "maxResults": min(max(max_results, 1), 50),
        "labelIds": ["INBOX"],
    }
    if page_token:
        list_kwargs["pageToken"] = page_token
    if query:
        list_kwargs["q"] = query

    try:
        results = service.users().messages().list(**list_kwargs).execute()
    except HttpError as e:
        raise RuntimeError(f"Gmail API communication error: {e.reason if hasattr(e, 'reason') else str(e)}")

    messages_meta = results.get("messages", [])
    next_page_token = results.get("nextPageToken")
    result_estimate = results.get("resultSizeEstimate", len(messages_meta))

    emails: List[Dict[str, Any]] = []

    for item in messages_meta:
        msg_id = item.get("id")
        if not msg_id:
            continue

        try:
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            parsed = parse_gmail_message(msg)
            emails.append(parsed)
        except Exception as parse_err:
            print(f"[IgnisGuard] Warning parsing message {msg_id}: {parse_err}")
            # Include minimal error record rather than dropping
            emails.append({
                "id": msg_id,
                "sender": "Unknown Sender",
                "senderName": "Unknown",
                "recipient": connected_email or "me",
                "subject": "(Error retrieving message details)",
                "date": datetime.datetime.utcnow().isoformat(),
                "snippet": "Failed to decode message",
                "body": "(Could not decode message content)",
                "isDemo": False,
            })

    return {
        "emails": emails,
        "next_page_token": next_page_token,
        "result_size_estimate": result_estimate,
        "connected_email": connected_email,
    }


def fetch_single_email(email_id: str) -> Dict[str, Any]:
    """Fetch a single full email by its Gmail message ID."""
    creds, _ = get_stored_credentials()
    if not creds or not creds.valid:
        raise PermissionError("Gmail is not connected. Please authenticate.")

    service = build("gmail", "v1", credentials=creds)
    try:
        msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        return parse_gmail_message(msg)
    except HttpError as e:
        raise RuntimeError(f"Gmail message {email_id} not found or inaccessible: {str(e)}")


def parse_gmail_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely parse raw Gmail API response into a normalized email dictionary.
    Handles multipart/mixed, multipart/alternative, HTML sanitization, character encodings.
    """
    payload = msg.get("payload", {})
    headers_list = payload.get("headers", [])
    headers: Dict[str, str] = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

    from_header = headers.get("from", "Unknown Sender")
    to_header = headers.get("to", "")
    subject_header = headers.get("subject", "(No Subject)")
    date_header = headers.get("date", "")

    # Decode body safely
    plain_text, html_text = _extract_mime_parts(payload)

    if plain_text.strip():
        final_body = plain_text
    elif html_text.strip():
        final_body = _sanitize_html_to_plaintext(html_text)
    else:
        final_body = msg.get("snippet", "(No message body content found)")

    return {
        "id": msg.get("id"),
        "threadId": msg.get("threadId"),
        "sender": from_header,
        "senderName": _extract_display_name(from_header),
        "recipient": to_header,
        "subject": subject_header,
        "date": _normalize_date(date_header, msg.get("internalDate")),
        "snippet": msg.get("snippet", ""),
        "body": final_body,
        "isDemo": False,
    }


def _extract_mime_parts(payload: Dict[str, Any]) -> Tuple[str, str]:
    """Recursively traverse MIME structure and extract plain text and HTML."""
    plain_parts: List[str] = []
    html_parts: List[str] = []

    def _traverse(part: Dict[str, Any]):
        mime_type = part.get("mimeType", "").lower()
        body_data = part.get("body", {}).get("data")

        if body_data:
            decoded = _safe_base64_decode(body_data)
            if "text/plain" in mime_type:
                plain_parts.append(decoded)
            elif "text/html" in mime_type:
                html_parts.append(decoded)

        # Recurse children
        for child in part.get("parts", []):
            _traverse(child)

    _traverse(payload)
    return "\n".join(plain_parts), "\n".join(html_parts)


def _safe_base64_decode(data_str: str) -> str:
    """Decode URL-safe base64 data handling missing padding and encoding varieties."""
    try:
        # Add missing base64 padding
        padded = data_str + "=" * (-len(data_str) % 4)
        raw_bytes = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return ""

    for encoding in ("utf-8", "latin-1", "windows-1252", "iso-8859-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw_bytes.decode("utf-8", errors="replace")


def _sanitize_html_to_plaintext(raw_html: str) -> str:
    """
    Converts HTML to sanitized plain text.
    Strips scripts, styles, dangerous tags, and decodes HTML entities.
    Prevents execution of any embedded instructions or HTML scripts.
    """
    if not raw_html:
        return ""

    # Remove script, style, and comments
    text = re.sub(r"(?is)<script.*?>.*?</script>", "", raw_html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)

    # Convert line breaking tags to newlines
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(p|div|tr|li|h[1-6])\b.*?>", "\n", text)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Unescape HTML entities (&nbsp;, &lt;, &gt;, etc.)
    text = html.unescape(text)

    # Normalize whitespace while preserving line structure
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join([line for line in lines if line])
    return text.strip()


def _extract_display_name(from_str: str) -> str:
    """Extract display name from RFC 822 From header."""
    if "<" in from_str:
        name = from_str.split("<")[0].strip().strip('"').strip("'")
        if name:
            return name
        # If name was empty before <email>, use email prefix
        match = re.search(r"<([^>]+)>", from_str)
        if match:
            return match.group(1).split("@")[0]
    return from_str.split("@")[0].strip()


def _normalize_date(date_str: str, internal_date: Optional[str] = None) -> str:
    """Format date into ISO 8601 string or fallback to internalDate timestamp."""
    if internal_date and internal_date.isdigit():
        try:
            ts = int(internal_date) / 1000.0
            return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"
        except Exception:
            pass
    return date_str or datetime.datetime.utcnow().isoformat() + "Z"
