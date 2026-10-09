"""Shared digest preferences, independent of rendering, delivery and business storage."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DigestState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    digest_enabled: bool = False
    digest_time: str = Field(default="09:00", pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    digest_not_before: float = Field(default=0, ge=0)
    digest_last_day: str | None = None

    @field_validator("digest_last_day")
    @classmethod
    def valid_day(cls, value):
        if value is not None and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Invalid digest date")
        return value
