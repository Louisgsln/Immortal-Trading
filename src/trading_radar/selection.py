"""Explain existing title filters without broadening role or employer rules."""

from collections import Counter
from typing import Literal

from trading_radar.models import SelectionSummary
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions


def rejection_reason(
    title: str, options: SearchOptions, *, verified_role: bool = False
) -> str | None:
    normalized = normalize_text(title)
    for term in options.exclude_title_terms:
        if has(normalized, term):
            return "excluded_title:" + normalize_text(term)
    if (
        not verified_role
        and options.title_terms
        and not any(has(normalized, term) for term in options.title_terms)
    ):
        return "no_title_match"
    return None


class SelectionAudit:
    def __init__(self, scope: Literal["public_catalogue", "search_results"]):
        self.scope = scope
        self.selected = 0
        self.rejected: Counter[str] = Counter()
        self.samples: list[dict[str, str]] = []

    def record(self, reason: str | None, title: str = "", identifier: str = "") -> None:
        if reason is None:
            self.selected += 1
            return
        self.rejected[reason] += 1
        # Hidden posts and prospects contribute only to counters, never to displayed titles.
        if title and len(self.samples) < 30:
            self.samples.append(
                {
                    "reason": reason,
                    "title": " ".join(title.split())[:240],
                    "external_id": identifier[:120],
                }
            )

    def summary(self) -> SelectionSummary:
        return SelectionSummary(
            scope=self.scope,
            examined=self.selected + sum(self.rejected.values()),
            selected=self.selected,
            rejected=dict(self.rejected),
            samples=self.samples,
        )
