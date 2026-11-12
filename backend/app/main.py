"""
CascadeIQ — FastAPI application entry point.
Wires up CORS, startup/shutdown lifecycle, and all routers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB.  Shutdown: nothing yet."""
    await init_db()
    print("✅  Database initialised")
    yield
    print("👋  CascadeIQ shutting down")


app = FastAPI(
    title="CascadeIQ",
    description="Disaster Risk & Resource Coordination Platform — Sutlej Basin Demo",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # wildcard origin requires credentials=False
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (imported lazily so circular-import issues stay local) ─────────────
from app.routers import zones, incidents, resources, optimizer, weather, ml  # noqa: E402

app.include_router(zones.router,      prefix="/api/zones",      tags=["Zones"])
app.include_router(incidents.router,  prefix="/api/incidents",  tags=["Incidents"])
app.include_router(resources.router,  prefix="/api/resources",  tags=["Resources"])
app.include_router(optimizer.router,  prefix="/api/optimizer",  tags=["Optimizer"])
app.include_router(weather.router,    prefix="/api/weather",    tags=["Weather"])
app.include_router(ml.router,         prefix="/api/ml",         tags=["ML Predictor"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "CascadeIQ online", "version": "0.1.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
