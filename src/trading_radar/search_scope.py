"""Bounded search configuration shared by public career adapters."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search_terms: list[str] = Field(
        default_factory=lambda: ["trading"], min_length=1, max_length=10
    )
    title_terms: list[str] = Field(
        default_factory=lambda: [
            "trading",
            "trader",
            "markets",
            "structuring",
            "structurer",
            "repo",
            "securities finance",
        ]
    )
    exclude_title_terms: list[str] = Field(
        default_factory=lambda: [
            "operations",
            "product control",
            "compliance",
            "audit",
            "market risk",
            "director",
            "vice president",
            "vp",
            "svp",
            "avp",
            "head of",
            "senior",
        ]
    )
    max_results_per_query: int = Field(default=1999, ge=1, le=1999)
    max_details: int = Field(default=250, ge=1, le=1000)
    max_scan_seconds: int = Field(default=600, ge=10, le=1800)

    @field_validator("search_terms")
    @classmethod
    def validate_terms(cls, terms: list[str]) -> list[str]:
        if any(not t.strip() or len(t) > 100 for t in terms):
            raise ValueError("Search terms must be nonempty and at most 100 characters")
        return list(dict.fromkeys(t.strip() for t in terms))
