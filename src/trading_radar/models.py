from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class ExperienceEvidence(BaseModel):
    minimum_years: int = Field(ge=0, le=99)
    kind: Literal["professional", "industry_or_academia", "unspecified"]
    origin: Literal["description"] = "description"
    method: Literal["jump_coding_track_record"] = "jump_coding_track_record"
    excerpt: str


class RawJob(BaseModel):
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    apply_url: str
    source: str
    source_type: Literal["official", "ats", "board", "aggregator", "fixture"] = "ats"
    external_id: str | None = None
    description: str = ""
    location: str = ""
    source_url: str = ""
    date_posted: datetime | None = None
    application_deadline: datetime | None = None
    expected_start_date: str | None = None
    employment_type: str | None = None
    minimum_experience_years: int | None = Field(default=None, ge=0, le=99)
    experience_evidence: list[ExperienceEvidence] = Field(default_factory=list)
    seniority_hint: Literal["junior", "senior"] | None = None
    role_hint: Literal["trading_technology"] | None = None
    remote: bool | None = None
    raw_payload: dict[str, Any] | None = None


class Score(BaseModel):
    trading: int = Field(default=0, ge=0, le=30)
    junior: int = Field(default=0, ge=0, le=20)
    start: int = Field(default=0, ge=0, le=15)
    front_office: int = Field(default=0, ge=0, le=15)
    asset: int = Field(default=0, ge=0, le=10)
    profile_fit: int = Field(default=0, ge=0, le=10)
    reasons: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)

    @property
    def total(self) -> int:
        if self.exclusions:
            return 0
        return sum(
            getattr(self, k)
            for k in ("trading", "junior", "start", "front_office", "asset", "profile_fit")
        )

    @property
    def priority(self) -> str:
        return (
            "URGENT"
            if self.total >= 85
            else "HIGH"
            if self.total >= 70
            else "MEDIUM"
            if self.total >= 55
            else "LOW"
        )


class Job(RawJob):
    id: str
    fingerprint: str
    company_normalized: str
    title_normalized: str
    description_text: str
    location_normalized: str
    city: str | None = None
    country: str | None = None
    region: str | None = None
    location_tier: int | None = None
    seniority: str = "unknown"
    programme_type: str | None = None
    desk: list[str] = Field(default_factory=list)
    asset_class: list[str] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=utcnow)
    last_seen: datetime = Field(default_factory=utcnow)
    date_updated: datetime = Field(default_factory=utcnow)
    score_breakdown: Score = Field(default_factory=Score)
    is_new: bool = True
    is_active: bool = True
    is_expired: bool = False

    def urgency(self, now: datetime | None = None) -> int:
        now = now or utcnow()
        age = max(0, (now - self.first_seen).total_seconds() / 3600)
        recent = 5 if age < 1 else 3 if age < 6 else 1 if age < 24 else 0
        days = (
            (self.application_deadline - now).total_seconds() / 86400
            if self.application_deadline
            else 999
        )
        deadline = 5 if 0 <= days <= 1 else 3 if 0 <= days <= 3 else 1 if 0 <= days <= 7 else 0
        return self.score_breakdown.total + recent + deadline


class Collection(BaseModel):
    jobs: list[RawJob]
    complete: bool = False
    requests: int = 0


class ScanMetrics(BaseModel):
    sources: int = 0
    successful: int = 0
    failed: dict[str, str] = Field(default_factory=dict)
    requests: int = 0
    received: int = 0
    new: int = 0
    updated: int = 0
    closed: int = 0
    relevant: int = 0
    high_priority: int = 0
    alerts: int = 0
    duration: float = 0
