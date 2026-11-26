from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.api.v1 import forecasts, villages, decisions, matches, burns

app = FastAPI(title="Residue Compass API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before the final demo
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(villages.router, prefix="/api/v1", tags=["villages"])
app.include_router(forecasts.router, prefix="/api/v1", tags=["forecast"])
app.include_router(decisions.router, prefix="/api/v1", tags=["decision"])
app.include_router(matches.router, prefix="/api/v1", tags=["matches"])
app.include_router(burns.router, prefix="/api/v1", tags=["burn-events"])


@app.get("/api/v1/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception:
        db = "down"
    return {"status": "ok", "database": db, "demo_mode": settings.DEMO_MODE}
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE}