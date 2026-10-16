"""
AI Agent Security — Configuration
Loads settings from environment variables with secure defaults.
"""

import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from backend directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google OAuth 2.0 (read-only Gmail)
    google_client_id: str = "280268833822-00m7mdod6anu91htdu6rucgpc5iskij4.apps.googleusercontent.com"
    google_client_secret: str = "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"
    google_redirect_uri: str = "http://localhost:8000/api/gmail/callback"

    # App URLs
    frontend_url: str = "http://localhost:5173"
    secret_key: str = secrets.token_urlsafe(32)

    # SQLite Database for server-side OAuth credentials and audit logs
    database_url: str = "sqlite:///./security_gate.db"

    # MiniMoth LLM API Key (paste your API key here or in .env)
    minimoth_api_key: str = "mm_test_9829e7b84fb37764f1ce0bfa6a7cfa2c5c5f3df3e09407f75c0ec6e3dbd7b18ad4bf60818f86e324be6b846e4b60c0b7"

    # Gmail API scope — STRICTLY READ-ONLY
    gmail_scopes: list[str] = ["https://www.googleapis.com/auth/gmail.readonly"]

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
        """Ensure non-empty defaults in this file take precedence over empty lines in .env."""
        for field_name in ("google_client_id", "google_client_secret", "minimoth_api_key"):
            val = getattr(self, field_name, "")
            if not val or not str(val).strip():
                default_val = self.__class__.model_fields[field_name].default
                if default_val and str(default_val).strip():
                    setattr(self, field_name, str(default_val).strip())
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
