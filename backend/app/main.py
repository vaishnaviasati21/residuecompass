"""
Root FastAPI application.

Mounts all v1 routers and sets up:
  - CORS
  - duplicate health endpoint fix (removed duplicate)
  - structured exception handler for validation errors
  - startup banner in demo mode
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings, validate_security_config
from app.core.db import engine

# Routers
from app.api.v1 import (
    auth,
    burns,
    buyers,
    decisions,
    demo,
    forecasts,
    jobs,
    matches,
    notifications,
    villages,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_config()
    mode = "DEMO" if settings.DEMO_MODE else "PRODUCTION"
    logger.info("=" * 60)
    logger.info(" Residue Compass API  –  mode: %s", mode)
    logger.info(" Docs: http://127.0.0.1:8000/docs")
    logger.info("=" * 60)
    yield


app = FastAPI(
    title="Residue Compass API",
    version="1.0.0",
    description=(
        "API for the Residue Compass paddy-straw management platform.\n\n"
        "**Roles**: officer (full access) · farmer (own village) · buyer (own matches)\n\n"
        "**Demo mode**: set `DEMO_MODE=true` to enable `/api/v1/demo/*` endpoints."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router,          prefix=PREFIX)
app.include_router(villages.router,      prefix=PREFIX, tags=["villages"])
app.include_router(forecasts.router,     prefix=PREFIX, tags=["forecast"])
app.include_router(decisions.router,     prefix=PREFIX)
app.include_router(matches.router,       prefix=PREFIX)
app.include_router(burns.router,         prefix=PREFIX, tags=["burn-events"])
app.include_router(buyers.router,        prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(jobs.router,          prefix=PREFIX)
app.include_router(demo.router,          prefix=PREFIX)


# ── Health ────────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["meta"])
def health():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return {
        "status": "ok",
        "database": db_status,
        "demo_mode": settings.DEMO_MODE,
        "version": "1.0.0",
    }


# ── Global error handler for Pydantic validation ──────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for e in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in e["loc"]),
            "message": e["msg"],
            "type": e["type"],
        })
    return JSONResponse(
        status_code=422,
        content={"detail": {"error": {"code": "VALIDATION_ERROR",
                                       "message": "One or more fields failed validation.",
                                       "fields": errors}}},
    )
