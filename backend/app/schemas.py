"""Pydantic request schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["individual", "researcher"] = "individual"
    institution_code: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if value.lower() in {"password", "12345678", "qwertyui"}:
            raise ValueError("Choose a less common password.")
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=120)
    organisation: str | None = Field(default=None, max_length=160)
    share_aggregate: bool | None = None
    store_raw_signals: bool | None = None
    allow_baseline: bool | None = None
    baseline_min_sessions: int | None = Field(default=None, ge=3, le=20)
    data_note: str | None = Field(default=None, max_length=1000)


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AccountDeleteIn(BaseModel):
    password: str


class SessionCreateIn(BaseModel):
    scenario: Literal["resting", "arousal", "activity", "noisy", "recovery"] = "resting"


class SessionTickIn(BaseModel):
    tick_seconds: float = Field(default=4.0, ge=1.0, le=15.0)


class UploadAnalysisIn(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    sampling_rate: float | None = Field(default=None, gt=0, le=20000)


class DemoAnalysisIn(BaseModel):
    dataset_id: str


class ReferenceAnalysisIn(BaseModel):
    subject: str | None = None
    label: Literal["neutral", "stress", "amusement"] | None = None


class ExperimentIn(BaseModel):
    dataset_id: str
    model: Literal["Random Forest", "Support Vector Machine", "Gradient Boosting", "XGBoost"] = "Random Forest"


class ReportIn(BaseModel):
    title: str | None = Field(default=None, max_length=220)
