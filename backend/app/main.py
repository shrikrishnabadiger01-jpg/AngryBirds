from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from urllib.parse import urlsplit
from app.auth import COOKIE_NAME, load_users, read_session, router as auth_router
from app.config import settings
from app.database import init_db
from app.routers import audit, health, workspace, evaluations, scripted_tests, gmail, emails

app = FastAPI(
    title="AI Agent Security API",
    description="FastAPI backend for AI Agent Security & Policy Enforcement Platform (Genesis 2.0)",
    version="2.0.0",
    docs_url=None if settings.app_env.lower() == "production" else "/docs",
    redoc_url=None if settings.app_env.lower() == "production" else "/redoc",
)

if settings.auth_enabled:
    load_users()

# Initialize SQLite database for credentials and audit logs
init_db()

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_control(request, call_next):
    path = request.url.path
    public_paths = {"/", "/api/health", "/api/auth/session", "/api/auth/login", "/api/auth/logout", "/api/gmail/callback"}
    user = None
    if settings.auth_enabled and request.method != "OPTIONS":
        user = read_session(request.cookies.get(COOKIE_NAME))
        if path not in public_paths:
            if not user:
                return JSONResponse({"detail": "Authentication required"}, status_code=401)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                request_origin, app_origin = urlsplit(origin), urlsplit(settings.frontend_url)
                if request_origin.scheme != app_origin.scheme or request_origin.netloc.lower() != app_origin.netloc.lower():
                    return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
    if not settings.auth_enabled:
        user = {"username": "local", "role": "admin"}
    request.state.user = user
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if path.startswith("/api/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response

app.include_router(health.router)
app.include_router(workspace.router)
app.include_router(evaluations.router)
app.include_router(scripted_tests.router)
app.include_router(gmail.router)
app.include_router(emails.router)
app.include_router(audit.router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "AI Agent Security API is operational",
        "docs": None if settings.app_env.lower() == "production" else "/docs",
        "health": "/api/health",
        "team": "Genesis 2.0 · Team Angry Birds",
    }
