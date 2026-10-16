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
    google_client_id: str = "280268833822-00m7mdod6anu91htdu6rucgpc5iskij4.apps.googleusercontent.com"
    google_client_secret: str = "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"
    google_redirect_uri: str = "http://localhost:8000/api/gmail/callback"

    # App URLs
    frontend_url: str = "http://localhost:5173"
    secret_key: str = ""
    app_env: str = "development"
    auth_enabled: bool = False
    auth_users_json: str = ""

    # SQLite Database for server-side OAuth credentials and audit logs
    database_url: str = "sqlite:///./security_gate.db"

    # Google Gemini API key. Set MINIMOTH_API_KEY or GEMINI_API_KEY in backend/.env.
    # Keep credentials out of source code; an empty value enables simulation mode.
    minimoth_api_key: str = ""

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
        """Backwards compatibility alias for has_minimoth_key."""
        return self.has_minimoth_key

    @property
    def gemini_api_key(self) -> str:
        """Backwards compatibility alias for minimoth_api_key."""
        return self.minimoth_api_key

    @model_validator(mode="after")
    def restore_class_defaults_if_empty(self):
        """Restore OAuth defaults if environment files contain empty values."""
        for field_name in ("google_client_id", "google_client_secret"):
            val = getattr(self, field_name, "")
            if not val or not str(val).strip():
                default_val = self.__class__.model_fields[field_name].default
                if default_val and str(default_val).strip():
                    setattr(self, field_name, str(default_val).strip())
        return self

    @model_validator(mode="after")
    def require_production_access_controls(self):
        if self.app_env.lower() == "production":
            if not self.auth_enabled:
                raise ValueError("AUTH_ENABLED=true is required in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters in production")
            if not self.auth_users_json.strip():
                raise ValueError("APP_USERS_JSON must configure at least one user in production")
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
