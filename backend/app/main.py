"""
AI SEO Auditor - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.api.v1.endpoints import audit, health
from app.logger import logger

# Create app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered SEO Audit Tool with Technical, Content, and AI SEO scoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1/audit")


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info(f"Starting {settings.APP_NAME}...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }
