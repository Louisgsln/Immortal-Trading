"""Role-evidence regression tests derived from the audited Jump posting patterns."""

import pytest

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

PYTHON_DUTIES = (
    "What You'll Do: Collaborate with traders to understand business requirements and "
    "design technical solutions. Design, code, test, deploy and support reliable software "
    "applications. Skills You’ll Need: At least 2 years of experience in Python programming."
)
QUANT_POSITION = (
    "As a Quantitative Developer, you will build and improve the platforms that drive the "
    "trading team. Work with quantitative researchers on research and trading infrastructure. "
    "What You'll Do: Full cycle development: writing, testing and debugging code. "
    "Support the production trading system. Skills You’ll Need: Python and C++."
)


def parse(title, content, *, department="Core Development", contract="Full-time - Experienced"):
    config = load_config().companies["jump_trading"]
    row = {
        "id": 1,
        "internal_job_id": 101,
        "company_name": "Jump Trading",
        "title": title,
        "absolute_url": "https://www.jumptrading.com/hr/job?gh_jid=1",
        "location": {"name": "London"},
        "content": content,
        "metadata": [{"name": "Employment Type", "value": contract}],
        "departments": [{"name": department}],
    }
    return parse_board(
        {"meta": {"total": 1}, "jobs": [row]}, "jump_trading", config, GreenhouseOptions()
    )


@pytest.mark.parametrize(
    "title,content,department",
    [
        ("Python Software Engineer", PYTHON_DUTIES, "Core Development "),
        ("Quantitative Developer", QUANT_POSITION, "Front Office "),
        ("Quantitative Developer | Trading Team", QUANT_POSITION, "Front Office"),
    ],
)
def test_verified_roles_are_selected_without_inventing_juniority(title, content, department):
    raw = parse(title, content, department=department)[0]
    assert raw.role_hint == "trading_technology"
    assert raw.seniority_hint is None and raw.expected_start_date is None
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.total > 0
    assert "software role without embedded trading evidence" not in job.score_breakdown.exclusions


@pytest.mark.parametrize("department", ["IT Infrastructure", "Human Resources", ""])
def test_mission_without_verified_department_does_not_extend_filter(department):
    assert not parse("Python Software Engineer", PYTHON_DUTIES, department=department)


@pytest.mark.parametrize(
    "content",
    [
        "Core Development builds our trading platform. What You'll Do: Build business tools. "
        "Skills You'll Need: Python.",
        "Collaborate with traders and design technical solutions and software applications. "
        "What You'll Do: Maintain corporate tools. Skills You'll Need: Python.",
        "What You'll Do: Support users. Skills You'll Need: Previously collaborate with traders "
        "to design technical solutions and software applications.",
        PYTHON_DUTIES.replace("What You'll Do:", ""),
        PYTHON_DUTIES + " What You'll Do: Duplicate role heading.",
        PYTHON_DUTIES.replace("Skills You’ll Need:", ""),
    ],
)
def test_boilerplate_requirements_and_ambiguous_sections_are_not_role_evidence(content):
    assert not parse("Software Engineer", content)


def test_production_support_alone_is_not_verified_quant_development():
    content = QUANT_POSITION.replace(
        "Full cycle development: writing, testing and debugging code.", ""
    )
    assert not parse("Quantitative Developer", content, department="Front Office")


def test_existing_senior_and_intern_exclusions_still_apply():
    assert not parse("Senior Python Software Engineer", PYTHON_DUTIES)
    raw = parse(
        "Python Software Engineer (Intern)", PYTHON_DUTIES, contract="Jump Trading - Intern"
    )[0]
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0
    raw = parse("Python Software Engineer", PYTHON_DUTIES.replace("2 years", "5 years"))[0]
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0
