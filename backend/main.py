"""
Last-Minute Life Saver — FastAPI entry point.
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import create_tables
from auth import init_firebase

# Import all models so SQLAlchemy registers them before create_tables()
import models  # noqa: F401

from routers import tasks, users, calendar, schedule, voice, agents

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Last-Minute Life Saver API…")
    init_firebase()
    await create_tables()
    logger.info("Ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Last-Minute Life Saver API",
    description="AI-powered productivity companion — Gemini function calling + Google Calendar + FCM",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(calendar.router)
app.include_router(schedule.router)
app.include_router(voice.router)
app.include_router(agents.router)


# ── Health + root ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Last-Minute Life Saver", "status": "ok", "docs": "/docs"}


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "healthy"}
