"""User-maintained application records, separate from collected job facts."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApplicationStatus(StrEnum):
    NEW = "New"
    REVIEWING = "Reviewing"
    TO_APPLY = "To Apply"
    APPLIED = "Applied"
    ONLINE_ASSESSMENT = "Online Assessment"
    VIDEO_INTERVIEW = "Video Interview"
    INTERVIEW = "Interview"
    FINAL_ROUND = "Final Round"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    CLOSED = "Closed"


class ApplicationField(StrEnum):
    APPLICATION_DATE = "application_date"
    RECRUITER = "recruiter"
    NOTES = "notes"
    NEXT_ACTION = "next_action"
    NEXT_ACTION_DATE = "next_action_date"


def calendar_date(value):
    if value is None or type(value) is date:
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        except ValueError:
            pass
    raise ValueError("Use a calendar date in YYYY-MM-DD format")


class Application(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: ApplicationStatus = ApplicationStatus.NEW
    application_date: date | None = None
    recruiter: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=20000)
    next_action: str | None = Field(default=None, max_length=2000)
    next_action_date: date | None = None

    @field_validator("application_date", "next_action_date", mode="before")
    @classmethod
    def dates(cls, value):
        return calendar_date(value)

    @field_validator("recruiter", "notes", "next_action")
    @classmethod
    def text(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def action_has_label(self):
        if self.next_action_date and not self.next_action:
            raise ValueError("A next action date requires a next action")
        return self
