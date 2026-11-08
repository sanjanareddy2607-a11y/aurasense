"""Institution aggregate analytics (privacy-preserving)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles
from ..models import User
from ..services.aggregate import institution_overview, overview_csv

router = APIRouter(prefix="/api/institution", tags=["institution"])


@router.get("/overview")
def overview(
    weeks: int = Query(default=8, ge=1, le=52),
    user: User = Depends(require_roles("researcher", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return institution_overview(db, weeks=weeks)


@router.get("/export")
def export(
    weeks: int = Query(default=8, ge=1, le=52),
    user: User = Depends(require_roles("researcher", "admin")),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    data = institution_overview(db, weeks=weeks)
    return PlainTextResponse(
        overview_csv(data),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="aurasense-aggregate.csv"'},
    )
