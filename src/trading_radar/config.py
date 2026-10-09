import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class Company(BaseModel):
    name: str
    enabled: bool = False
    ats: str
    tenant: str = ""
    career_url: str = ""
    country: str = ""
    scan_interval: int = Field(default=300, ge=60)
    request_interval: float = Field(default=2, ge=0.1)
    notes: str = ""
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant")
    @classmethod
    def validate_tenant(cls, value: str) -> str:
        if value and not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("tenant must be an ATS board slug")
        return value


class Settings(BaseModel):
    bootstrap_silent: bool = True
    alert_min_score: int = Field(default=70, ge=0, le=100)
    concurrency: int = Field(default=4, ge=1, le=16)
    timeout: float = Field(default=20, gt=0, le=120)
    retries: int = Field(default=3, ge=0, le=5)
    source_timeout: float = Field(default=600, ge=10, le=1800)
    store_raw: bool = False
    closure_after_missing_scans: int = Field(default=2, ge=2)
    database_url: str = "sqlite:///data/jobs.db"
    alerts_enabled: bool = False
    telegram_control_enabled: bool = False
    telegram_incident_notices_enabled: bool = False
    deadline_reminders_enabled: bool = False
    deadline_reminder_max_age_hours: float = Field(default=24, gt=0, le=168)
    include_internships: bool = False
    internship_alerts_enabled: bool = False
    internship_formats: list[Literal["off_cycle", "long"]] = Field(
        default=["off_cycle", "long"], min_length=1
    )
    internship_target_year: int = Field(default=2027, ge=2026, le=2100)
    internship_baseline_at: datetime | None = None

    @field_validator("internship_baseline_at")
    @classmethod
    def aware_baseline(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("internship_baseline_at requires a timezone")
        return value.astimezone(UTC) if value is not None else None


class Config(BaseModel):
    settings: Settings
    companies: dict[str, Company]
    keywords: dict[str, list[str]]


def load_config(directory: Path = Path("config")) -> Config:
    load_dotenv(override=False)
    settings = yaml.safe_load((directory / "settings.yaml").read_text(encoding="utf-8")) or {}
    for env, key in [
        ("DATABASE_URL", "database_url"),
        ("ALERTS_ENABLED", "alerts_enabled"),
        ("TELEGRAM_CONTROL_ENABLED", "telegram_control_enabled"),
        ("TELEGRAM_INCIDENT_NOTICES_ENABLED", "telegram_incident_notices_enabled"),
    ]:
        if env in os.environ:
            settings[key] = os.environ[env]
    companies = yaml.safe_load((directory / "companies.yaml").read_text(encoding="utf-8"))
    keywords = yaml.safe_load((directory / "keywords.yaml").read_text(encoding="utf-8"))
    return Config(
        settings=Settings(**settings), companies=companies["companies"], keywords=keywords
    )
