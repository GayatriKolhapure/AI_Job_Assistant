"""FastAPI Application Main Entry Point."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.database.connection import init_db
from backend.app.api.health import router as health_router
from backend.app.api.applications import router as applications_router
from backend.app.api.resume import router as resume_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.chat import router as chat_router

logger = logging.getLogger("uvicorn.error")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing SQLite applications database...")
    init_db()
    logger.info(f"Database initialized at: {settings.database_url}")
    yield
    logger.info("Shutting down AI Job Assistant service...")


app = FastAPI(
    title=settings.app_name,
    description="Production-quality AI Job Chat Assistant API with LangGraph orchestration, resume parsing, and application tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Exception Handler
@app.exception_handler(Exception)
async def sanitized_exception_handler(request, exc: Exception):
    logger.error(f"Internal error processing {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again or verify inputs."},
    )

# Root endpoint
@app.get("/", tags=["Info"])
def get_root():
    return {
        "app_name": settings.app_name,
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "description": "Conversational AI Job Assistant for Hidani Tech Assessment",
    }

# Include routers
app.include_router(health_router)
app.include_router(applications_router)
app.include_router(resume_router)
app.include_router(jobs_router)
app.include_router(chat_router)
