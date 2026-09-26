import pytest

from trading_radar.education import education_mentions
from trading_radar.html_page import Document
from trading_radar.missions import mission_excerpts
from trading_radar.optiver_sections import description_html

BODY = "<p><strong>What you’ll do</strong></p><p>Under supervision:</p><ul><li>Quote options.<ul><li>Within desk limits.</li></ul></li><li>Research signals.</li><li>Review positions.</li><li>Keep full records.</li></ul><p><strong>Who you are</strong></p><ul><li>Master’s degree preferred, or equivalent experience.</li></ul>"


def parsed_job(job, content=BODY):
    job.source = "optiver"
    job.description = description_html(Document(content).root)
    return job


def test_optiver_complete_items_keep_intro_conditions_and_degree_alternatives(job):
    j = parsed_job(job)
    before = j.model_dump()
    assert mission_excerpts(j) == {
        "heading": "What you’ll do",
        "excerpts": [
            "Under supervision: Quote options. Within desk limits.",
            "Research signals.",
            "Review positions.",
        ],
    }
    assert education_mentions(j)["levels"] == ["master"]
    assert (
        education_mentions(j)["evidence"][0]["excerpt"]
        == "Master’s degree preferred, or equivalent experience."
    )
    assert "Keep full records." in j.description
    assert j.model_dump() == before


@pytest.mark.parametrize(
    "content",
    [
        BODY + BODY,
        BODY.replace("<p><strong>Who you are</strong></p>", ""),
        BODY.replace("What you’ll do", "Who we are"),
        BODY.replace("<p>Under supervision:</p>", "<h3>Benefits</h3>"),
        BODY.replace("<p>Under supervision:</p>", "<p><strong>Benefits</strong></p>"),
        BODY.replace("<p>Under supervision:</p>", "Unbounded words"),
        BODY.replace(
            "<p><strong>Who you are</strong></p>",
            "<p>Additional conditions after the list.</p><p><strong>Who you are</strong></p>",
        ),
        BODY.replace("Under supervision:", "x" * 1501),
        BODY.replace(
            "<p><strong>Who you are</strong></p>", "</div><div><p><strong>Who you are</strong></p>"
        ),
        BODY.replace("<p>Under supervision:</p>", "<div><p>Another wrapper</p></div>"),
    ],
)
def test_ambiguous_or_unbounded_optiver_missions_remain_unknown(job, content):
    assert mission_excerpts(parsed_job(job, "<div>" + content + "</div>")) is None


@pytest.mark.parametrize(
    "attributes",
    ["hidden", 'aria-hidden="true"', 'style="display: none"', 'style="visibility:hidden"'],
)
def test_hidden_sections_are_not_evidence(job, attributes):
    j = parsed_job(job, f"<section {attributes}>" + BODY + "</section>")
    assert mission_excerpts(j) is None
    assert education_mentions(j)["levels"] == []


def test_hidden_content_does_not_turn_unlabelled_lists_into_evidence(job):
    job = parsed_job(
        job, BODY.replace("<p>Under supervision:</p>", "<p hidden>Hidden condition</p>")
    )
    assert mission_excerpts(job) is None


def test_optiver_degree_sections_are_specific_to_employer_and_keep_negation(job):
    j = parsed_job(job, "<p>Who you are</p><ul><li>A PhD is not required.</li></ul>")
    assert education_mentions(j)["evidence"][0]["excerpt"] == "A PhD is not required."
    j.source = "unsupported"
    assert education_mentions(j)["levels"] == []
    assert mission_excerpts(j) is None
