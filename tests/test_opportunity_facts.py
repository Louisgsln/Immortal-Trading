from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.opportunity_facts import country_facts, duration_facts, start_facts


def job(**values):
    return normalize(
        RawJob(
            company="Synthetic",
            title="2027 Trading Internship",
            apply_url="https://example.com/job",
            source="fixture",
            **values,
        )
    )


def test_countries_preserve_identity_and_handle_multiple_locations():
    j = job(location="London, United Kingdom; Paris, France")
    before = (j.id, j.fingerprint, j.location_normalized, j.country)
    assert [c["code"] for c in country_facts(j)["countries"]] == ["FR", "GB"]
    assert before == (j.id, j.fingerprint, j.location_normalized, j.country)
    assert country_facts(job(location="Paris, United States"))["countries"][0]["code"] == "US"
    assert country_facts(job(location="Undisclosed / remote"))["precision"] == "unknown"


def test_duration_words_ranges_and_no_previous_experience():
    assert (
        duration_facts(
            job(description="<p>The internship programme runs for Six to nine months.</p>")
        )["min_months"]
        == 6
    )
    assert duration_facts(job(description="<p>Durée : 6 à 12 mois.</p>"))["max_months"] == 12
    for text in [
        "Previous internship of 6 months required.",
        "Application duration: 6 months.",
        "Requirements: six months of experience.",
        "<script>Duration: 6 months.</script>",
    ]:
        assert duration_facts(job(description=text))["precision"] == "unknown"
    assert (
        duration_facts(job(description="Duration: 6 months. Duration: 9 months."))["precision"]
        == "conflict"
    )


def test_start_exact_months_and_unknowns():
    assert start_facts(job(expected_start_date="2027-03-15"))["windows"] == [
        {"from": "2027-03-15", "to": "2027-03-15"}
    ]
    assert start_facts(job(description="Start date: March to April 2027."))["windows"] == [
        {"from": "2027-03-01", "to": "2027-03-31"},
        {"from": "2027-04-01", "to": "2027-04-30"},
    ]
    assert (
        start_facts(job(description="Applications close in March 2027. Graduating in 2027."))[
            "windows"
        ]
        == []
    )
    assert (
        start_facts(job(expected_start_date="2027", description="Start: January 2028."))["windows"]
        == []
    )
