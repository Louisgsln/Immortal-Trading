"""Source-specific proofs; fixture clauses are copied from the lot 41 audit."""

import html

import pytest

from trading_radar.config import Company
from trading_radar.experience import experience_requirement
from trading_radar.macquarie import DETAIL, SEARCH, parse_detail
from trading_radar.macquarie_experience import macquarie_sales_trading_evidence
from trading_radar.normalizer import normalize, plain_text
from trading_radar.scoring import score_job

REQUIREMENT = "5 years’ of experience in sales trading, including client coverage and new business development"
PARAGRAPH = (
    REQUIREMENT + " Proven ability to build and manage institutional client relationships, with "
    "interest in the hedge fund segment Strong account management skills and experience "
    "working in a global, team-oriented environment Solid understanding of risk management "
    "and trading operations in institutional equity markets Series 7, 63, and 55 licenses, "
    "with strong academic credentials, ideally in a quantitative or technology field"
)


def field(value, label="", cls=""):
    label_html = f'<div class="article__content__view__field__label">{label}</div>' if label else ""
    return (
        f'<div class="article__content__view__field {cls}">{label_html}'
        f'<div class="article__content__view__field__value">{value}</div></div>'
    )


def parse(requirements=PARAGRAPH, responsibilities="Trade cash equities"):
    title = "Institutional Cash Equity Sales Trader"
    content = (
        f'<h2 class="title--11">{title}</h2><article class="article__content__fields">'
        + field("23225", "Job ID", "field--jobcategory")
        + field("New York", "Additional office locations", "field--location")
        + field("Permanent - Full time", cls="field--employmentterm")
        + '</article><section class="section--without--border--top">'
        + "<article><h3>What role will you play?</h3>"
        + field(responsibilities)
        + "</article><article><h3>What you offer</h3>"
        + field(requirements)
        + "</article></section>"
    )
    config = Company(name="Macquarie", ats="macquarie", career_url=SEARCH)
    row = {"id": "23225", "title": title, "url": DETAIL + "?jobId=23225"}
    return parse_detail(content, row, config, "macquarie")


def test_collector_attaches_exact_professional_proof_and_excludes_senior_job(config):
    raw = parse()
    assert raw.minimum_experience_years == 5
    assert len(raw.experience_evidence) == 1
    evidence = raw.experience_evidence[0]
    assert evidence.model_dump() == {
        "minimum_years": 5,
        "kind": "professional",
        "origin": "description",
        "method": "macquarie_sales_trading_experience",
        "excerpt": REQUIREMENT,
    }
    assert evidence.excerpt in plain_text(raw.description)
    job = score_job(normalize(raw), config.keywords)
    assert job.score_breakdown.total == 0
    assert experience_requirement(job)["minimum_years"] == 5
    assert experience_requirement(job)["category"] == "over_2"
    assert job.experience_evidence == raw.experience_evidence


def test_collector_scopes_new_proof_to_what_you_offer():
    raw = parse("Strong communication skills", responsibilities=PARAGRAPH)
    assert raw.minimum_experience_years is None and raw.experience_evidence == []


def test_higher_historical_range_still_wins():
    raw = parse(PARAGRAPH + " 6-10 years’ experience trading rates")
    assert raw.minimum_experience_years == 6
    assert raw.experience_evidence[0].minimum_years == 5


@pytest.mark.parametrize("minimum", [0, 2, 5, 99])
def test_bounded_integer_values(minimum):
    clause = f"{minimum} years of experience in sales trading."
    proof = macquarie_sales_trading_evidence("<p>" + clause + "</p>")
    assert [item.minimum_years for item in proof] == [minimum]
    assert proof[0].excerpt == clause


@pytest.mark.parametrize("prefix", ["Ideally ", "Up to ", "Our team has ", "A doctorate or "])
def test_non_requirement_prefixes_are_not_inferred(prefix):
    assert macquarie_sales_trading_evidence("<p>" + prefix + REQUIREMENT + "</p>") == []


@pytest.mark.parametrize(
    "suffix",
    [
        " preferred",
        " is not required",
        " or a doctorate",
        " or 2 years in industry",
        " is optional",
        " would be advantageous",
        " may be waived",
        " rather than a contract",
        " for our team since it was established",
    ],
)
def test_uncertain_duration_never_becomes_professional_minimum(suffix):
    assert macquarie_sales_trading_evidence("<p>" + REQUIREMENT + suffix + "</p>") == []


@pytest.mark.parametrize("number", ["100", "-5", "1.5", "05", "2-5", "5-2", "5+", "٥"])
def test_new_rule_does_not_accept_ranges_malformed_or_unreviewed_numbers(number):
    content = f"<p>{number} years of experience in sales trading.</p>"
    assert macquarie_sales_trading_evidence(content) == []


def test_entities_and_inline_markup_preserve_rendered_excerpt():
    content = "<p><strong>5 years’</strong> of experience in sales trading &amp; execution.</p>"
    proof = macquarie_sales_trading_evidence(content)
    assert len(proof) == 1 and proof[0].excerpt == plain_text(content)


def test_hidden_or_unbounded_content_is_ignored():
    for content in (
        PARAGRAPH,
        "<div>" + PARAGRAPH + "</div>",
        "<script>" + html.escape("<p>" + PARAGRAPH + "</p>") + "</script>",
        "<template><p>" + PARAGRAPH + "</p></template>",
    ):
        assert macquarie_sales_trading_evidence(content) == []


def test_identical_paragraph_proofs_are_deduplicated():
    proof = macquarie_sales_trading_evidence(("<p>" + REQUIREMENT + "</p>") * 2)
    assert len(proof) == 1


def test_independent_paragraphs_preserve_their_proofs():
    content = "<p>5 years of experience in sales trading.</p><p>7 years of experience in sales trading.</p>"
    proof = macquarie_sales_trading_evidence(content)
    assert [item.minimum_years for item in proof] == [5, 7]
