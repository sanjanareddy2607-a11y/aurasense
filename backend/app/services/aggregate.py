"""Privacy-preserving institutional aggregates.

Only analyses from users who explicitly opted in (``share_aggregate``) are
included.  Small groups are suppressed entirely; no per-user row is returned.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AnalysisResult, Profile, User

MIN_USERS_PER_GROUP = 3


def _week_start(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    monday = value - timedelta(days=value.weekday())
    return monday.date().isoformat()


def institution_overview(db: Session, weeks: int = 8) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    stmt = (
        select(AnalysisResult, User)
        .join(User, User.id == AnalysisResult.user_id)
        .join(Profile, Profile.user_id == User.id)
        .where(Profile.share_aggregate.is_(True))
        .where(AnalysisResult.created_at >= since.replace(tzinfo=None))
        .where(AnalysisResult.predicted_class.is_not(None))
        .order_by(AnalysisResult.created_at.asc())
    )
    rows = list(db.execute(stmt).all())

    groups: dict[str, list[tuple[AnalysisResult, User]]] = defaultdict(list)
    for analysis, user in rows:
        groups[_week_start(analysis.created_at)].append((analysis, user))

    weekly = []
    suppressed = 0
    for week, entries in sorted(groups.items()):
        users = {user.id for _, user in entries}
        if len(entries) < settings.institution_min_cohort or len(users) < MIN_USERS_PER_GROUP:
            suppressed += 1
            continue
        probs = [a.stress_score for a, _ in entries if a.stress_score is not None]
        qualities = [a.quality_score for a, _ in entries if a.quality_score is not None]
        confidences = [a.confidence for a, _ in entries if a.confidence is not None]
        classes = Counter(a.predicted_class for a, _ in entries)
        weekly.append(
            {
                "week_start": week,
                "sessions": len(entries),
                "participants": len(users),
                "mean_stress_probability": round(sum(probs) / len(probs), 1) if probs else None,
                "stress_share": round(100.0 * classes.get("stress", 0) / len(entries), 1),
                "neutral_share": round(100.0 * classes.get("neutral", 0) / len(entries), 1),
                "amusement_share": round(100.0 * classes.get("amusement", 0) / len(entries), 1),
                "mean_quality": round(sum(qualities) / len(qualities), 1) if qualities else None,
                "mean_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
                "demo_sessions": sum(1 for a, _ in entries if a.is_demo),
            }
        )

    included = [entry for week in groups.values() for entry in week]
    included_users = {u.id for _, u in included}
    class_totals: Counter = Counter()
    for analysis, _ in included:
        class_totals[analysis.predicted_class] += 1
    total = sum(class_totals.values()) or 1
    consenting = db.scalar(
        select(Profile).where(Profile.share_aggregate.is_(True)).limit(1)
    )
    consenting_users = len(
        list(db.scalars(select(Profile).where(Profile.share_aggregate.is_(True))))
    )

    source_counts: Counter = Counter()
    for analysis, _ in included:
        source_counts[analysis.source_type] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_weeks": weeks,
        "min_cohort": settings.institution_min_cohort,
        "summary": {
            "sessions": len(included),
            "participants": len(included_users),
            "consenting_users": consenting_users,
            "mean_stress_probability": round(
                sum(a.stress_score for a, _ in included if a.stress_score is not None)
                / max(1, sum(1 for a, _ in included if a.stress_score is not None)),
                1,
            )
            if included
            else None,
            "mean_quality": round(
                sum(a.quality_score for a, _ in included if a.quality_score is not None)
                / max(1, sum(1 for a, _ in included if a.quality_score is not None)),
                1,
            )
            if included
            else None,
            "demo_sessions": sum(1 for a, _ in included if a.is_demo),
        },
        "weekly": weekly,
        "class_distribution": {
            name: {"count": count, "share": round(100.0 * count / total, 1)}
            for name, count in class_totals.items()
        },
        "sources": dict(source_counts),
        "privacy": {
            "suppressed_groups": suppressed,
            "min_sessions_per_group": settings.institution_min_cohort,
            "min_participants_per_group": MIN_USERS_PER_GROUP,
            "opted_in": bool(consenting),
            "note": (
                "Only aggregate statistics from users who opted in are shown. Groups with fewer than "
                f"{settings.institution_min_cohort} sessions or {MIN_USERS_PER_GROUP} participants are suppressed. "
                "No individual prediction, email or identifier is exposed."
            ),
            "demo_data_included": any(a.is_demo for a, _ in included),
        },
        "disclaimer": (
            "Aggregates reflect self-reported, simulated or uploaded recordings and must not be used for "
            "surveillance, performance evaluation or clinical decisions."
        ),
    }


def overview_csv(overview: dict[str, Any]) -> str:
    lines = [
        "week_start,sessions,participants,mean_stress_probability,stress_share,neutral_share,amusement_share,mean_quality,demo_sessions"
    ]
    for row in overview["weekly"]:
        lines.append(
            ",".join(
                str(row.get(key, ""))
                for key in (
                    "week_start",
                    "sessions",
                    "participants",
                    "mean_stress_probability",
                    "stress_share",
                    "neutral_share",
                    "amusement_share",
                    "mean_quality",
                    "demo_sessions",
                )
            )
        )
    lines.append("")
    lines.append(f"# minimum cohort: {overview['min_cohort']} sessions and {MIN_USERS_PER_GROUP} participants")
    lines.append(f"# suppressed groups: {overview['privacy']['suppressed_groups']}")
    lines.append(f"# {overview['privacy']['note']}")
    return "\n".join(lines)
