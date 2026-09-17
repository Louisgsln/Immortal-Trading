import pytest

from trading_radar.models import Job, RawJob
from trading_radar.normalizer import normalize
from trading_radar.role_evidence import role_evidence_text

CORPORATE = (
    "Headquartered in Chicago with offices throughout the U.S., Canada, Europe, and Asia, "
    "we trade a variety of asset classes including Fixed Income, ETFs, Equities, FX, "
    "Commodities and Energy across all major global markets. We have also leveraged "
    "our expertise and technology to expand into three non-traditional strategies: "
    "real estate, venture capital and cryptoassets."
)
PREDICTION = (
    "DRW is a major Chicago-based proprietary trading firm founded in 1992 by Don Wilson, "
    "specializing in diversified, technology-driven market-making and quantitative trading "
    "across asset classes including fixed income, options, derivatives, commodities, "
    "energy, equities, FX, and cryptocurrency."
)


def job(text: str) -> Job:
    result = normalize(
        RawJob(
            company="DRW",
            title="Trader",
            apply_url="https://job-boards.greenhouse.io/drweng/jobs/1",
            source="drw",
            source_type="official",
            description=text,
        )
    )
    # The helper's contract is the preserved text, not regenerated HTML.
    result.description_text = text
    return result


@pytest.mark.parametrize("passage", [CORPORATE, PREDICTION])
def test_remove_only_complete_audited_passage(passage: str) -> None:
    original = (
        "Trade rates using Python.\n" + passage + "\nManage FX options after the introduction."
    )
    item = job(original)
    before = item.model_dump()
    assert (
        role_evidence_text(item)
        == "Trade rates using Python.\n\nManage FX options after the introduction."
    )
    assert item.model_dump() == before


def test_two_verified_passages_preserve_interleaved_roles() -> None:
    item = job(CORPORATE + "\nPrice credit derivatives.\n" + PREDICTION + "\nTrade ETFs.")
    assert role_evidence_text(item) == "\nPrice credit derivatives.\n\nTrade ETFs."


def test_repeated_passage_does_not_truncate_surrounding_text() -> None:
    item = job("Start. " + CORPORATE + " Role one. " + CORPORATE + " Role two.")
    assert role_evidence_text(item) == "Start.  Role one.  Role two."


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\t", "\u00a0", "   "])
def test_only_whitespace_variation_is_tolerated(separator: str) -> None:
    item = job("Trade FX.\n" + CORPORATE.replace(" ", separator) + "\nTrade crypto.")
    assert role_evidence_text(item) == "Trade FX.\n\nTrade crypto."


@pytest.mark.parametrize(
    "text",
    [
        CORPORATE.split(" We have also")[0],
        "We have also" + CORPORATE.split(" We have also")[1],
        CORPORATE.replace("Commodities and Energy", "Commodities, and Energy"),
        CORPORATE.replace("including Fixed Income", "including Options, Fixed Income"),
        CORPORATE.replace("we trade", "you will trade"),
        CORPORATE.replace("expertise and technology", "expertise and Python technology"),
        CORPORATE.replace(". We have also", ". You will price rates. We have also"),
        CORPORATE.lower(),
        CORPORATE[:-1],
        PREDICTION.replace("founded in 1992", "founded in 1993"),
        "We trade FX, equities and commodities with Python and SQL.",
        "About DRW: Our options desk trades listed derivatives.",
        "About the role. You will trade crypto and FX.",
        "Not" + CORPORATE,
        CORPORATE + "UnexpectedContinuation",
        "",
    ],
)
def test_partial_modified_unknown_and_role_text_remain_intact(text: str) -> None:
    assert role_evidence_text(job(text)) == text


@pytest.mark.parametrize(
    "changes",
    [
        {"company": "Other Firm"},
        {"company_normalized": "other firm"},
        {"source": "other_source"},
        {"source_type": "aggregator"},
        {"source_type": "board"},
        {"source_type": "ats"},
        {"source_type": "fixture"},
    ],
)
def test_employer_and_official_source_are_both_required(changes: dict) -> None:
    item = job(CORPORATE).model_copy(update=changes)
    assert role_evidence_text(item) == CORPORATE


def test_does_not_recover_removed_text_from_original_html() -> None:
    item = job("Trade credit.")
    item.description = "<p>" + CORPORATE + "</p><p>Trade FX using SQL.</p>"
    assert role_evidence_text(item) == "Trade credit."


def test_preserved_text_controls_even_when_html_differs() -> None:
    item = job(CORPORATE + "\nTrade credit.")
    item.description = "<p>Trade FX using SQL.</p>"
    assert role_evidence_text(item) == "\nTrade credit."


def test_result_is_idempotent() -> None:
    item = job(CORPORATE + "\nTrade options.")
    item.description_text = role_evidence_text(item)
    assert role_evidence_text(item) == "\nTrade options."
