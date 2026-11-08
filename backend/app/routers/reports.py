"""Report generation and download."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import AnalysisResult, Dataset, Report, ResearchExperiment, User
from ..schemas import ReportIn
from ..services import inference, reporting
from ..services.aggregate import institution_overview
from ..services.serializers import report_dict

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Report).where(Report.user_id == user.id).order_by(desc(Report.created_at)).limit(100)
    ).all()
    return {"reports": [report_dict(r) for r in rows]}


@router.post("/analysis/{analysis_id}", status_code=201)
def analysis_report(
    analysis_id: str,
    payload: ReportIn | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    analysis = db.get(AnalysisResult, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    report = reporting.analysis_report(db, user, analysis)
    if payload and payload.title:
        report.title = payload.title
        db.commit()
        db.refresh(report)
    return {"report": report_dict(report), "notice": "PDF generated from the stored analysis."}


@router.post("/research")
def research_report(
    payload: ReportIn | None = None,
    experiment_id: str | None = None,
    user: User = Depends(require_roles("researcher", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    dataset = db.scalars(select(Dataset).where(Dataset.is_reference.is_(True))).first()
    if experiment_id:
        experiment = db.get(ResearchExperiment, experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="Experiment not found.")
        dataset = db.get(Dataset, experiment.dataset_id) or dataset
        metrics = json.loads(experiment.metrics)
        metrics.setdefault("best_model", experiment.model_type)
        metrics.setdefault("classes", ["neutral", "stress", "amusement"])
        metrics.setdefault("evaluation_strategy", experiment.evaluation_strategy)
        metrics.setdefault("per_subject", metrics.get("per_subject", {}))
    else:
        metrics = inference.load_metrics()
        experiment = None
    if metrics is None:
        raise HTTPException(status_code=503, detail="No evaluation metrics are available yet.")
    if dataset is None:
        raise HTTPException(status_code=404, detail="No reference dataset is registered.")
    report = reporting.research_report(db, user, dataset, metrics, experiment)
    if payload and payload.title:
        report.title = payload.title
        db.commit()
        db.refresh(report)
    return {"report": report_dict(report)}


@router.post("/institution")
def institution_report(
    payload: ReportIn | None = None,
    weeks: int = 8,
    user: User = Depends(require_roles("researcher", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    overview = institution_overview(db, weeks=max(1, min(weeks, 52)))
    report = reporting.institution_report(db, user, overview)
    if payload and payload.title:
        report.title = payload.title
        db.commit()
        db.refresh(report)
    return {"report": report_dict(report), "notice": "Aggregate-only report; no individual records included."}


@router.get("/{report_id}/download")
def download(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(status_code=410, detail="Report file is missing. Regenerate it.")
    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=f"aurasense-{report.kind}-{report.id[:8]}.pdf",
    )


@router.delete("/{report_id}")
def delete_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.file_path:
        Path(report.file_path).unlink(missing_ok=True)
    db.delete(report)
    db.commit()
    return {"ok": True}
