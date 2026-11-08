"""Health, metadata and model information."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..services import inference
from ..services.simulation import SCENARIOS

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.api_version,
        "environment": settings.environment,
        "database": "ok" if db_ok else "unavailable",
        "model_available": inference.is_available(),
    }


@router.get("/model/info")
def model_info() -> dict:
    return inference.model_info()


@router.get("/meta")
def meta() -> dict:
    return {
        "product": "AuraSense",
        "tagline": "Beyond the pulse. Understand the pattern.",
        "version": settings.api_version,
        "scenarios": [
            {
                "key": key,
                "label": value["label"],
                "description": value["description"],
                "is_simulation": True,
            }
            for key, value in SCENARIOS.items()
        ],
        "disclaimer": (
            "AuraSense is a research and wellbeing-support tool. It does not diagnose anxiety, depression or any "
            "other condition, and it does not measure mental stress directly. Physiological signals are affected by "
            "movement, caffeine, illness, temperature and many other factors."
        ),
        "simulation_notice": "Live monitoring uses clearly labelled simulated signals generated on the server.",
        "roles": {
            "individual": "Own physiological data, analyses, baselines and reports.",
            "researcher": "Research Centre, experiment execution, research reports and aggregate insights.",
            "admin": "Institution-level aggregate analytics and research features.",
        },
        "privacy": {
            "aggregate_opt_in": "Institution aggregates only include users who explicitly opt in.",
            "min_cohort": settings.institution_min_cohort,
        },
        "dataset": {
            "name": "WESAD (Wearable Stress and Affect Detection)",
            "citation": "Schmidt, P., & Reiss, A. (2018). DOI: 10.24432/C57K5T",
            "url": "https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detect",
            "paper": "https://www.eti.uni-siegen.de/ubicomp/papers/ubi_icmi2018.pdf",
        },
    }
