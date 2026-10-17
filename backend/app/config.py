"""
AI Agent Security — Configuration
Loads settings from environment variables with secure defaults.
"""

from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from backend directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google OAuth 2.0 Gmail access
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/gmail/callback"

    # App URLs
    frontend_url: str = "http://localhost:5173"
    secret_key: str = ""
    app_env: str = "development"
    auth_enabled: bool = False
    auth_mode: str = "password"
    auth_default_role: str = "operator"
    auth_users_json: str = ""

    # SQLite Database for server-side OAuth credentials and audit logs
    database_url: str = "sqlite:///./security_gate.db"

    # MiniMoth OTP API credentials and Google Gemini model credentials are separate.
    minimoth_api_key: str = ""
    gemini_api_key: str = ""

    # Gmail API scopes; send actions remain approval-gated in the workspace.
    gmail_scopes: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    @property
    def has_google_credentials(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    @property
    def has_minimoth_key(self) -> bool:
        return bool(self.minimoth_api_key.strip())

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @model_validator(mode="after")
    def require_production_access_controls(self):
        if self.auth_mode not in {"password", "minimoth_otp"}:
            raise ValueError("AUTH_MODE must be 'password' or 'minimoth_otp'")
        if self.auth_default_role not in {"admin", "operator", "auditor"}:
            raise ValueError("AUTH_DEFAULT_ROLE must be admin, operator, or auditor")
        if self.auth_mode == "minimoth_otp" and self.auth_enabled and not self.minimoth_api_key.strip():
            raise ValueError("MINIMOTH_API_KEY is required when MiniMoth OTP authentication is enabled")
        if self.auth_enabled and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters when authentication is enabled")
        if self.app_env.lower() == "production":
            if not self.auth_enabled:
                raise ValueError("AUTH_ENABLED=true is required in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters in production")
            if self.auth_mode == "password" and not self.auth_users_json.strip():
                raise ValueError("APP_USERS_JSON must configure at least one user in production")
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
