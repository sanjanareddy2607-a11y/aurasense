"""AuraSense FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal, init_db
from .routers import (
    analysis,
    auth,
    baseline,
    datasets,
    institution,
    reports,
    research,
    sessions,
    system,
)

logger = logging.getLogger("aurasense")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

if settings.environment == "production" and settings.secret_key == "dev-only-change-me-aurasense":
    raise RuntimeError(
        "Production requires a private SECRET_KEY; set it in the deployment environment."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    if settings.seed_demo:
        try:
            from .seed import seed_if_needed

            with SessionLocal() as db:
                seed_if_needed(db)
        except Exception:  # seeding must never stop the API from starting
            logger.exception("Demo seeding failed; the API will start without seed data")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description=(
        "AuraSense — AI-assisted physiological stress-pattern analysis. "
        "Estimates describe similarity to WESAD research conditions and are not medical conclusions."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


for router in (
    system.router,
    auth.router,
    sessions.router,
    analysis.router,
    datasets.router,
    baseline.router,
    research.router,
    reports.router,
    institution.router,
):
    app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "product": "AuraSense",
        "tagline": "Beyond the pulse. Understand the pattern.",
        "api": "/api",
        "docs": "/docs",
    }
