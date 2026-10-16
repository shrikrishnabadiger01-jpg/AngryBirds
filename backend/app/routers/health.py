from fastapi import APIRouter
from app.config import settings
from app.services import gmail_service

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def get_health():
    g_status = gmail_service.get_connection_status()

    return {
        "status": "healthy",
        "auth_required": settings.auth_enabled,
        "service": "AI Agent Security (Genesis 2.0)",
        "version": "2.0.0",
        "auth_mode": settings.auth_mode,
        "minimoth_api_key_configured": settings.has_minimoth_key,
        "gemini_api_key_configured": settings.has_gemini_key,
        "mode": "live_gemini" if settings.has_gemini_key else "simulation_fallback",
        "gmail_configured": g_status.get("configured", False),
        "gmail_connected": g_status.get("connected", False),
    }
