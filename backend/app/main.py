from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.init_db import init_database

settings = get_settings()
setup_logging(level="DEBUG" if settings.APP_ENV == "development" else "INFO")
logger = logging.getLogger("safezone.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SafeZone Backend API in %s mode", settings.APP_ENV)
    try:
        await init_database()
        logger.info("Database schemas and seed accounts successfully initialized.")
    except Exception as exc:
        logger.warning("Database initialization notice: %s", exc)
    yield
    logger.info("Shutting down SafeZone Backend API")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# CORS Configuration - allow all in dev for Web/Mobile communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# Include API router
app.include_router(api_router)
