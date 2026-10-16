"""
AI Agent Security — Gmail OAuth Router
Handles Google OAuth 2.0 flow with CSRF state verification,
server-side token storage in SQLite, and secure disconnect.
Never exposes OAuth client secrets or access tokens to the browser.
"""

import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, OAuthState
from app.services import gmail_service

router = APIRouter(prefix="/api/gmail", tags=["Gmail"])


@router.get("/auth")
async def start_oauth(db: Session = Depends(get_db)):
    """
    Generate Google OAuth 2.0 authorization URL.
    Saves a one-time CSRF state token to SQLite.
    """
    if not settings.has_google_credentials:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google OAuth credentials not configured on the server. "
                "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env"
            ),
        )

    try:
        auth_url, state = gmail_service.get_auth_url()

        # Save CSRF state with 10-minute validity
        db_state = OAuthState(state=state, created_at=datetime.datetime.utcnow(), used="false")
        db.add(db_state)
        db.commit()

        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Google OAuth flow: {str(e)}")


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Google OAuth callback endpoint.
    Verifies CSRF state, exchanges authorization code for tokens,
    stores credentials in SQLite, and redirects to frontend.
    """
    if error:
        return RedirectResponse(url=f"{settings.frontend_url}?gmail=error&reason={error}")

    if not code or not state:
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=error&reason=Missing+authorization+code+or+state"
        )

    # Validate state parameter for CSRF protection
    db_state = db.query(OAuthState).filter(OAuthState.state == state).first()
    if not db_state:
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=error&reason=Invalid+state+parameter+(potential+CSRF+attack)"
        )

    if db_state.used == "true":
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=error&reason=OAuth+state+already+consumed"
        )

    age = datetime.datetime.utcnow() - db_state.created_at
    if age.total_seconds() > 600:
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=error&reason=OAuth+state+expired.+Please+try+again."
        )

    # Mark state as used
    db_state.used = "true"
    db.commit()

    try:
        result = gmail_service.handle_oauth_callback(code=code, state=state)
        user_email = result.get("email", "")
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=connected&email={user_email}"
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}?gmail=error&reason={str(e)}"
        )


@router.get("/status")
async def gmail_status():
    """Return Gmail connection status without exposing tokens."""
    return gmail_service.get_connection_status()


@router.post("/disconnect")
async def disconnect_gmail():
    """
    Revoke Google OAuth token and remove credentials from server database.
    """
    success = gmail_service.delete_credentials()
    return {"connected": False, "disconnected": success, "message": "Gmail account disconnected successfully."}
