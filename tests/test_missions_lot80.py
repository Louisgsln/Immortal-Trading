import pytest

from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts


def test_jane_street_complete_paragraphs_preserve_conditions(job):
    job.source = "jane_street"
    job.description = "<h3>About the Position</h3><p>Trade only within desk limits.</p><p>Research, with supervision.</p><p>No overnight risk.</p><p>Fourth paragraph remains in full description.</p><h3>About You</h3><ul><li>Master’s degree preferred, or equivalent experience.</li></ul>"
    before = job.model_dump()
    assert mission_excerpts(job) == {
        "heading": "About the Position",
        "excerpts": [
            "Trade only within desk limits.",
            "Research, with supervision.",
            "No overnight risk.",
        ],
    }
    assert education_mentions(job)["levels"] == ["master"]
    assert job.model_dump() == before


@pytest.mark.parametrize(
    "body",
    [
        "<h3>About the Position</h3><p>Trade.</p>",
        "<h3>About You</h3><p>Trade.</p><h3>About the Position</h3>",
        "<h3>About the Position</h3><p>Trade.</p><h4>Benefits</h4><p>Insurance.</p><h3>About You</h3>",
        "<h3>About the Position</h3>Unbounded text<p>Trade.</p><h3>About You</h3>",
        "<h3>About the Position</h3><p>Trade.</p><h3>About You</h3>" * 2,
        "<h3>About the Position</h3><p hidden>Trade.</p><h3>About You</h3>",
        "<h3>About the Position</h3><p>" + "x" * 1501 + "</p><h3>About You</h3>",
        "<h3>About the Position</h3><p>Trade.</p><h3>About You</h3><h3>About the Position</h3>",
    ],
)
def test_jane_street_ambiguous_sections_fall_back(job, body):
    job.source = "jane_street"
    job.description = body
    assert mission_excerpts(job) is None


@pytest.mark.parametrize("heading", ["What You Need to Succeed", "What you will need to succeed"])
def test_flow_nested_responsibilities_and_degree_alternatives(job, heading):
    job.source = "flow_traders"
    job.description = f"<h4>What You Will Do</h4><ul><li>Make markets<ul><li>Within limits.</li></ul></li></ul><h4>{heading}</h4><ul><li>University degree, preferably in Finance, or equivalent experience.</li></ul>"
    assert mission_excerpts(job)["excerpts"] == ["Make markets Within limits."]
    assert education_mentions(job)["levels"] == ["unspecified_level"]
    job.source = "unsupported"
    assert mission_excerpts(job) is None
    assert education_mentions(job)["levels"] == []
