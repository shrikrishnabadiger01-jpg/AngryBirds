from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import health, workspace, evaluations, scripted_tests, gmail, emails

app = FastAPI(
    title="AI Agent Security API",
    description="FastAPI backend for AI Agent Security & Policy Enforcement Platform (Genesis 2.0)",
    version="2.0.0",
)

# Initialize SQLite database for credentials and audit logs
init_db()

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(workspace.router)
app.include_router(evaluations.router)
app.include_router(scripted_tests.router)
app.include_router(gmail.router)
app.include_router(emails.router)


@app.get("/")
def root():
    return {
        "message": "AI Agent Security API is operational",
        "docs": "/docs",
        "health": "/api/health",
        "team": "Genesis 2.0 · Team Angry Birds",
    }
