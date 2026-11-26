from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import forecasts

app = FastAPI(title="Residue Compass API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecasts.router, prefix="/api/v1", tags=["forecast"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE}