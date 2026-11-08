"""Application configuration.

Values are read from environment variables (optionally via a .env file at the
project root).  SQLite is the default database so the project runs without a
server install; set DATABASE_URL to a PostgreSQL DSN to use PostgreSQL.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


class Settings:
    app_name: str = "AuraSense API"
    api_version: str = "1.0.0"
    environment: str = _env("AURASENSE_ENV", "development")

    secret_key: str = _env("SECRET_KEY", "dev-only-change-me-aurasense")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(_env("ACCESS_TOKEN_MINUTES", "720"))

    data_dir: Path = Path(_env("DATA_DIR", str(BACKEND_DIR / "data")))
    storage_dir: Path = Path(_env("STORAGE_DIR", str(BACKEND_DIR / "storage")))
    artifacts_dir: Path = Path(
        _env("ARTIFACTS_DIR", str(BACKEND_DIR / "ml" / "artifacts"))
    )
    wesad_dir: Path = Path(_env("WESAD_DIR", str(PROJECT_ROOT / "WESAD")))

    database_url: str = _env(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'data' / 'aurasense.db').as_posix()}"
    )

    cors_origins: list[str] = [
        o.strip()
        for o in _env(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        ).split(",")
        if o.strip()
    ]

    max_upload_bytes: int = int(_env("MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))
    institution_min_cohort: int = int(_env("INSTITUTION_MIN_COHORT", "5"))
    research_invite_code: str = _env("RESEARCH_INVITE_CODE", "AURA-RESEARCH")
    seed_demo: bool = _env("SEED_DEMO", "1") == "1"

    # Demonstration credentials.  The defaults are intentionally convenient for
    # local development; production deployments should override every value
    # below with a strong, private password.
    demo_individual_password: str = _env("DEMO_INDIVIDUAL_PASSWORD", "Demo1234!")
    demo_researcher_password: str = _env("DEMO_RESEARCHER_PASSWORD", "Research1234!")
    demo_admin_password: str = _env("DEMO_ADMIN_PASSWORD", "Institution1234!")
    demo_cohort_password: str = _env("DEMO_COHORT_PASSWORD", "DemoCohort123!")

    def ensure_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.storage_dir,
            self.storage_dir / "uploads",
            self.storage_dir / "reports",
            self.artifacts_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
