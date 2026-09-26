"""Complete SG profile paragraphs and literal Bac+4/Bac+5 observations."""

import html

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.telegram_cards import format_alert


def observed(job, description, source="societe_generale"):
    return job.model_copy(update={"source": source, "description": description})


def profile(body, heading="Et si c’était vous ?"):
    return f"<p>{heading} {body}</p>"


@pytest.mark.parametrize(
    "wording,levels",
    [
        (
            "Vous préparez un Bac+4/5 en école d'ingénieur, avec une spécialité en Finance.",
            ["bac_plus_4", "bac_plus_5"],
        ),
        ("Vous êtes étudiant en Bac + 5 en école de commerce.", ["bac_plus_5"]),
        (
            "Vous préparez un Bac + 4 / 5 ; une première expérience est un avantage.",
            ["bac_plus_4", "bac_plus_5"],
        ),
        ("Un Bac+4 est souhaité, sans être obligatoire.", ["bac_plus_4"]),
        ("Bac+5 ou expérience équivalente ; anglais courant.", ["bac_plus_5"]),
        (
            "Bac+4 ou Bac+5, selon le parcours, avec une expérience équivalente acceptée.",
            ["bac_plus_4", "bac_plus_5"],
        ),
        ("Pas de Bac+5 obligatoire ; expérience équivalente acceptée.", ["bac_plus_5"]),
        ("Bac+5 ; un master’s degree est également cité.", ["master", "bac_plus_5"]),
    ],
)
def test_bac_observations_preserve_full_conditions_without_degree_equivalence(job, wording, levels):
    current = observed(job, html.escape(profile(wording)))
    before = current.model_dump()
    assert education_mentions(current) == {
        "levels": levels,
        "evidence": [
            {"heading": "Et si c’était vous ?", "excerpt": wording, "levels": levels},
        ],
    }
    assert current.model_dump() == before


@pytest.mark.parametrize(
    "heading,body,levels",
    [
        (
            "Et si c'était vous ?",
            "De formation supérieure de type master, grande école d'Ingénieurs ou 3ème cycle universitaire.",
            ["master"],
        ),
        (
            "Profile required",
            "Bachelor’s or Master's degree in Financial Engineering, Physics, Mathematics or equivalent experience. English required.",
            ["bachelor", "master"],
        ),
        (
            "Profile required",
            "Preferred Majors: Master of Financial Engineering. This is a preference, not a minimum.",
            ["master"],
        ),
        (
            "Profile required",
            "Relevant bachelor/master degree holders. Or students expecting to obtain their degree before starting.",
            ["bachelor", "master"],
        ),
        (
            "Profile required",
            "A degree in Finance or equivalent professional experience.",
            ["unspecified_level"],
        ),
    ],
)
def test_profile_wording_keeps_preferences_alternatives_and_graduation_conditions(
    job, heading, body, levels
):
    current = observed(
        job,
        "<p>Vos missions au quotidien Our team includes PhDs.</p>"
        + profile(body, heading)
        + "<p>Pourquoi nous choisir ? Doctoral degree tuition support.</p>",
    )
    assert education_mentions(current) == {
        "levels": levels,
        "evidence": [
            {"heading": heading, "excerpt": body, "levels": levels},
        ],
    }


@pytest.mark.parametrize(
    "description",
    [
        profile("Bachelor degree required.") * 2,
        profile("Bac+4.") + profile("Bac+5.", "Profile required"),
        "<p>For example: Profile required Bachelor degree.</p>",
        "<p>Et si c’était vous ?</p><p>Bac+5.</p>",
        "<h3>Profile required</h3><p>Bachelor degree.</p>",
        "<div>" + profile("Bac+5.") + "</div>",
        profile("Bachelor degree " + "x" * 1500),
        profile("Vous avez une formation supérieure et maîtrisez les outils de trading."),
        profile(
            "MS Office, master trading tools and a high degree of accuracy.", "Profile required"
        ),
        profile("Vous préparez un Bac+40."),
        profile("Vous préparez un Bac+4/50."),
        profile("Vous préparez un Bac+4 / 6."),
        profile("Vous préparez un Bac+5G."),
        profile("Vous préparez un Bac+3."),
    ],
)
def test_unrecognized_ambiguous_or_incomplete_profiles_do_not_create_evidence(job, description):
    assert education_mentions(observed(job, description)) == {"levels": [], "evidence": []}


@pytest.mark.parametrize(
    "wrapper", ["<div hidden>{}</div>", "<script>{}</script>", "<template>{}</template>"]
)
def test_hidden_profile_is_never_evidence(job, wrapper):
    assert not education_mentions(observed(job, wrapper.format(profile("Bac+5."))))["evidence"]


def test_hidden_fragments_and_paragraphs_are_ignored(job):
    current = observed(
        job,
        "<p hidden>Profile required Doctoral degree.</p>"
        + profile(
            "Vous préparez un <strong>Bac+4/5</strong> avec une expérience équivalente acceptée.<span hidden> Doctoral degree.</span>"
        ),
    )
    result = education_mentions(current)
    assert result["levels"] == ["bac_plus_4", "bac_plus_5"]
    assert (
        result["evidence"][0]["excerpt"]
        == "Vous préparez un Bac+4/5 avec une expérience équivalente acceptée."
    )


@pytest.mark.parametrize(
    "source", ["credit_agricole_cib", "bnp_paribas", "workday", "societe_generale_campus"]
)
def test_profile_reader_is_scoped_to_the_audited_source(job, source):
    assert not education_mentions(observed(job, profile("Bac+4/5 ou de type master."), source))[
        "evidence"
    ]


def test_new_french_forms_do_not_expand_other_supported_sources(job):
    current = observed(
        job, "<p>Requirements</p><ul><li>Bac+4/5 ou de type master.</li></ul>", "morgan_stanley"
    )
    assert not education_mentions(current)["evidence"]


def test_repeated_bac_mentions_are_unique(job):
    result = education_mentions(observed(job, profile("Bac+4/5, puis Bac+5 selon votre parcours.")))
    assert result["levels"] == ["bac_plus_4", "bac_plus_5"]
    assert len(result["evidence"]) == 1


def test_dashboard_exposes_bac_filters_and_preserves_applied_status(config, repo, job, tmp_path):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    original = observed(job, "<p>Vos missions au quotidien Trade bonds.</p>")
    current = observed(
        job,
        original.description
        + html.escape(profile("Bac+4/5, spécialité &lt;/script&gt;&lt;img onerror=x&gt;.")),
    )
    assert format_alert(current, "new") == format_alert(original, "new")
    assert mission_excerpts(current) is None
    with repo.transaction():
        repo.upsert(current)
    repo.update_application(current.id, {"status": "Applied", "notes": "Follow up next week"})
    before = list(repo.db.iterdump())
    data = build_dashboard_data(config, tmp_path / "history")
    result = data["jobs"][0]
    assert result["education"]["levels"] == ["bac_plus_4", "bac_plus_5"]
    assert (
        result["education"]["evidence"][0]["excerpt"]
        == "Bac+4/5, spécialité </script><img onerror=x>."
    )
    assert result["score"] == current.score_breakdown.total
    assert result["application"]["status"] == "Applied"
    assert result["first_seen"] == current.first_seen.isoformat()
    rendered = render_dashboard(data)
    assert '<option value="bac_plus_4">Bac+4</option>' in rendered
    assert '<option value="bac_plus_5">Bac+5</option>' in rendered
    assert "</script><img onerror=x>" not in rendered
    assert list(repo.db.iterdump()) == before
