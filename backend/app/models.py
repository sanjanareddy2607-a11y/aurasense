"""SQLAlchemy models for AuraSense."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(24), default="individual")  # individual | researcher | admin
    status: Mapped[str] = mapped_column(String(16), default="active")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    organisation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    share_aggregate: Mapped[bool] = mapped_column(Boolean, default=False)
    store_raw_signals: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_baseline: Mapped[bool] = mapped_column(Boolean, default=True)
    baseline_min_sessions: Mapped[int] = mapped_column(Integer, default=5)
    data_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="simulated")
    scenario: Mapped[str] = mapped_column(String(32), default="resting")
    status: Mapped[str] = mapped_column(String(16), default="active")
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    signal_file: Mapped[str | None] = mapped_column(Text, nullable=True)

    analyses: Mapped[list["AnalysisResult"]] = relationship(back_populates="session")

    __table_args__ = (Index("ix_sessions_user_started", "user_id", "started_at"),)


class SignalAsset(Base):
    __tablename__ = "signal_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("monitoring_sessions.id", ondelete="SET NULL"), nullable=True
    )
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(160))
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    channels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    sampling_rates: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("monitoring_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), default="Analysis session")
    source_type: Mapped[str] = mapped_column(String(24), default="upload")  # upload | simulated | wesad_reference
    source_label: Mapped[str] = mapped_column(String(200), default="")
    model_version: Mapped[str] = mapped_column(String(40), default="unavailable")
    predicted_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    predicted_label: Mapped[str] = mapped_column(String(80), default="Insufficient signal quality")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    class_probabilities: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quality_issues: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON (measured, not imputed)
    imputed_features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    window_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    session: Mapped[MonitoringSession | None] = relationship(back_populates="analyses")


class BaselineRecord(Base):
    __tablename__ = "baselines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    features: Mapped[str] = mapped_column(Text)  # JSON {feature: {mean, std}}
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    session_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(200), default="upload")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_meta: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    channels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    sampling_rates: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    participant_count: Mapped[int] = mapped_column(Integer, default=0)
    label_distribution: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    class_names: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResearchExperiment(Base):
    __tablename__ = "research_experiments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_type: Mapped[str] = mapped_column(String(60))
    evaluation_strategy: Mapped[str] = mapped_column(String(80))
    metrics: Mapped[str] = mapped_column(Text)  # JSON
    model_version: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24), default="analysis")  # analysis | research | institution
    title: Mapped[str] = mapped_column(String(220))
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True
    )
    experiment_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_experiments.id", ondelete="SET NULL"), nullable=True
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
