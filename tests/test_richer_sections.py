import pytest

from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts


def observe(job, source, description):
    return job.model_copy(update={"source": source, "description": description})


@pytest.mark.parametrize("preface", ["", "Preferred qualifications, not mandatory:<br>"])
def test_ubs_mixed_criteria_preserve_nested_bullets_and_preferences(job, preface):
    current = observe(
        job,
        "ubs_professionals",
        "<h2>Your skills and experience</h2>"
        + preface
        + "• university degree in Finance<br>• Platforms:<br>o Bloomberg<br>o OBS<br>"
        "Preferred Skills<br>• Master’s degree is a plus<br>You are:<br>• curious"
        "<h2>About us</h2>Our team has PhDs",
    )
    result = education_mentions(current)
    assert result["levels"] == ["unspecified_level", "master"]
    assert "Preferred Skills Master’s degree is a plus" in result["evidence"][1]["excerpt"]
    assert all(("not mandatory" in row["excerpt"]) == bool(preface) for row in result["evidence"])


def test_ubs_publishing_marker_does_not_drop_degree_or_accept_changed_marker(job):
    body = '<h2>Your skills and experience</h2>• Degree in Physics<br><font color="white">*LI-GB</font><h2>About us</h2>'
    assert education_mentions(observe(job, "ubs_professionals", body))["levels"] == [
        "unspecified_level"
    ]
    assert not education_mentions(
        observe(job, "ubs_professionals", body.replace("*LI-GB", "or equivalent experience"))
    )["levels"]


@pytest.mark.parametrize("ending", ["Your Career Comeback", "The team"])
def test_ubs_missions_bounded_by_next_employer_field(job, ending):
    body = f"<h2>Key responsibilities</h2>We are looking for someone to:<br>• execute orders<br>• price options<br>• manage risk<br>• build tools<h2>{ending}</h2>Company promotion"
    result = mission_excerpts(observe(job, "ubs_professionals", body))
    assert result["excerpts"] == [
        "We are looking for someone to: execute orders",
        "We are looking for someone to: price options",
        "We are looking for someone to: manage risk",
    ]
    assert (
        mission_excerpts(
            observe(job, "ubs_professionals", body.replace(f"<h2>{ending}", "<h2>Benefits"))
        )
        is None
    )
    assert (
        mission_excerpts(
            observe(
                job,
                "ubs_professionals",
                body.replace("• price options", "or equivalent experience"),
            )
        )
        is None
    )


def test_tokyo_required_and_preferred_sections_are_separate(job):
    body = "<p>Introduction<br><b>To be considered for this program, you must:</b></p><p><br>• successfully complete an undergraduate or postgraduate degree between September 2027 – June 2028<br><br>I<b>deally, you would also have:</b></p><p>• unrestricted work authorisation in Japan</p>"
    result = education_mentions(observe(job, "barclays", body))
    assert result["levels"] == ["unspecified_level"]
    assert result["evidence"][0]["excerpt"].endswith("between September 2027 – June 2028")
    assert "Japan" not in result["evidence"][0]["excerpt"]
    assert not education_mentions(
        observe(
            job,
            "barclays",
            body.replace("I<b>deally, you would also have:", "<b>Unknown boundary:"),
        )
    )["levels"]
    assert not education_mentions(observe(job, "barclays", body * 2))["levels"]


@pytest.mark.parametrize(
    "wrapper", ["<div hidden>{}</div>", "<template>{}</template>", "<script>{}</script>"]
)
def test_bnp_degree_field_ignores_hidden_ancestors(job, wrapper):
    body = "<p><strong>Education Level:</strong> Bachelor’s degree or equivalent</p>"
    assert (
        education_mentions(observe(job, "bnp_paribas", body))["evidence"][0]["excerpt"]
        == "Bachelor’s degree or equivalent"
    )
    assert not education_mentions(observe(job, "bnp_paribas", wrapper.format(body)))["levels"]
    assert not education_mentions(observe(job, "bnp_paribas", body * 2))["levels"]
