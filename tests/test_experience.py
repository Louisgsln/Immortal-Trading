import pytest

from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.experience import experience_requirement


@pytest.mark.parametrize(
    ("description", "structured", "minimum", "category"),
    [
        ("", None, None, "unspecified"),
        ("At least 0 years of experience", None, 0, "up_to_2"),
        ("At least 2 years of experience", None, 2, "up_to_2"),
        ("At least 3 years of experience", None, 3, "over_2"),
        ("5+ years of relevant experience", None, 5, "over_2"),
        ("At least 2–5 years of experience", None, 2, "up_to_2"),
        ("At least 3-5+ years of experience", None, 3, "over_2"),
        ("At least 5-2 years of experience", None, None, "unspecified"),
        ("Preferably 5+ years of experience", None, None, "unspecified"),
        ("3+ years of experience is preferred", None, None, "unspecified"),
        ("Experience Desirable: 1+ years of relevant experience", None, None, "unspecified"),
        ("Ideally 7+ years of experience. Requires 2 years of experience.", None, 2, "up_to_2"),
        ("At least 2 years of experience. Minimum 5 years of experience.", None, 5, "over_2"),
        ("Minimum 5 years of experience. At least 2 years of experience.", None, 5, "over_2"),
        ("", 0, 0, "up_to_2"),
        ("", 2, 2, "up_to_2"),
        ("", 3, 3, "over_2"),
        ("", 5, 5, "over_2"),
        ("At least 2 years experience", 5, 5, "over_2"),
        ("At least 5 years experience", 2, 5, "over_2"),
        ("At least 3 years experience", 0, 3, "over_2"),
        ("5+ years of experience preferred", 0, 0, "up_to_2"),
        ("5+ years of experience preferred", 3, 3, "over_2"),
        ("Prior experience is helpful but not required", None, None, "unspecified"),
        ("Several years of trading experience", None, None, "unspecified"),
        ("Requires five years of experience", None, None, "unspecified"),
        ("Bachelor's degree plus 7 years of progressive experience", None, 7, "over_2"),
    ],
)
def test_recognized_experience_reuses_existing_rules(
    job, description, structured, minimum, category
):
    item = job.model_copy(
        update={"description_text": description, "minimum_experience_years": structured}
    )
    before = item.model_dump()
    assert experience_requirement(item) == {"minimum_years": minimum, "category": category}
    assert item.model_dump() == before


@pytest.mark.parametrize("structured", ["three", "3", "", True, False, 3.0, {}, [], -1, 100])
def test_unknown_unvalidated_metadata_is_not_coerced(job, structured):
    item = job.model_copy(update={"description_text": "", "minimum_experience_years": structured})
    assert experience_requirement(item) == {"minimum_years": None, "category": "unspecified"}


def test_unrecognized_metadata_does_not_hide_recognized_text(job):
    item = job.model_copy(
        update={
            "description_text": "At least 3 years of experience",
            "minimum_experience_years": "unknown",
        }
    )
    assert experience_requirement(item) == {"minimum_years": 3, "category": "over_2"}


@pytest.mark.parametrize(
    ("title", "hint"),
    [("Graduate Trader", "junior"), ("Junior Trader", None), ("Senior Trader", "senior")],
)
def test_title_and_seniority_do_not_imply_numeric_requirement(job, title, hint):
    item = job.model_copy(
        update={
            "description_text": "Trade options.",
            "minimum_experience_years": None,
            "title": title,
            "seniority_hint": hint,
        }
    )
    assert experience_requirement(item) == {"minimum_years": None, "category": "unspecified"}


@pytest.mark.parametrize(
    ("description", "structured", "minimum", "category"),
    [
        ("Trade FX", None, None, "unspecified"),
        ("Trade FX", 0, 0, "up_to_2"),
        ("At least 2-5 years of experience", None, 2, "up_to_2"),
        ("Minimum 3 years experience", None, 3, "over_2"),
        ("5+ years of experience preferred", 5, 5, "over_2"),
    ],
)
def test_dashboard_exports_experience_without_changing_database(
    config, repo, job, tmp_path, description, structured, minimum, category
):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    item = job.model_copy(
        update={"description_text": description, "minimum_experience_years": structured}
    )
    with repo.transaction():
        repo.upsert(item)
    before = list(repo.db.iterdump())
    result = build_dashboard_data(config, tmp_path / "history")
    assert result["status"] == "ok"
    assert len(result["jobs"]) == 1
    exported = result["jobs"][0]
    assert exported["experience"] == {"minimum_years": minimum, "category": category}
    assert exported["score_breakdown"] == item.score_breakdown.model_dump(mode="json")
    assert exported["score"] == item.score_breakdown.total
    assert exported["description_text"] == description
    assert list(repo.db.iterdump()) == before
