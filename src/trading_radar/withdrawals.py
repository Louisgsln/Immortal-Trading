"""Exact public SuccessFactors filled-page evidence, with canonical identity checks."""

from collections.abc import Callable

from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import SourceUnavailable
from trading_radar.models import WithdrawnPosting

FILLED = "Sorry, this position has been filled."


def filled_posting(
    text: str, row: dict, job_url: Callable[[str], tuple[str, str]]
) -> WithdrawnPosting | None:
    nodes = list(Document(text).root.walk())
    shells = with_class(nodes, "jobDisplayShell")
    if len(shells) != 1 or clean(shells[0]) != FILLED:
        return None
    canonical = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if len(canonical) != 1:
        raise SourceUnavailable("Filled posting canonical URL missing or ambiguous")
    url, identifier = job_url(canonical[0])
    if identifier != row["id"]:
        raise SourceUnavailable("Filled posting identity mismatch")
    return WithdrawnPosting(
        external_id=identifier, apply_url=url, evidence="employer_filled_message"
    )
