"""
AI Agent Security — Database Setup
SQLite database for persistent server-side OAuth credentials and security audit logs with SQLAlchemy.
"""

import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class AuditLog(Base):
    """Audit log entry for every security decision and scan."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)  # EMAIL_SCAN, THREAT_BLOCKED, etc.
    email_id = Column(String(100), nullable=True)
    sender = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    decision = Column(String(20), nullable=False)  # ALLOW, BLOCK, SUSPICIOUS
    reason = Column(Text, nullable=False)
    threat_level = Column(String(20), nullable=True)  # safe, low, medium, high, critical
    raw_indicators = Column(Text, nullable=True)  # JSON string of detected indicators


class OAuthState(Base):
    """Stores OAuth state parameters for CSRF protection."""

    __tablename__ = "oauth_states"

    state = Column(String(100), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    used = Column(String(5), default="false")


class UserCredential(Base):
    """
    Stores Google OAuth credentials securely on the server.
    Never exposed to the frontend.
    """

    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(String(255), default="https://oauth2.googleapis.com/token")
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)
    scopes = Column(Text, nullable=False)  # JSON encoded list of scopes
    expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
