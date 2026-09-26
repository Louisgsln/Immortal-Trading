from copy import deepcopy

import pytest

from trading_radar.runtime_status import format_incident_notice, format_status


@pytest.fixture
def report():
    return {
        "health": {
            "generated_at": "2026-09-26T19:11:55Z",
            "latest_scan": "2026-09-26T19:11:52Z",
            "database": {"status": "ok"},
            "sources": [
                {"source": str(i), "company": f"Bank {i}", "status": "fresh"} for i in range(40)
            ],
            "source_summary": {"fresh": 40},
            "issues": [],
        },
        "watcher": {"status": "active", "at": "2026-09-26T19:11:55Z"},
        "deliveries": {"sent": 4},
        "alerts_enabled": True,
        "threshold": 70,
    }


def test_recovery_is_three_short_lines_without_full_status(report):
    assert format_incident_notice(report) == (
        "✅ Radar opérationnel\n\n40/40 sources à jour · alertes actives\n26/09/2026 · 21:11"
    )
    report["alerts_enabled"] = False
    assert "alertes désactivées" in format_incident_notice(report)


def test_captcha_only_shows_problem_and_earliest_retry(report):
    report["health"]["sources"][0].update(
        source="nomura_campus",
        company="Nomura",
        status="access_restricted",
        failure={"label": "Le site demande un CAPTCHA."},
        schedule={"eligible_now": False, "next_eligible_at": "2026-09-26T19:23:34Z"},
    )
    report["health"]["source_summary"] = {"fresh": 39, "access_restricted": 1}
    report["health"]["issues"] = [{"code": "source_access_restricted", "source": "nomura_campus"}]
    before = deepcopy(report)
    text = format_incident_notice(report)
    assert "Nomura · Campus · accès bloqué · CAPTCHA" in text
    assert "Reprise possible dès 26/09/2026 · 21:23" in text
    assert "39/40 sources à jour" in text and "Détails · /status" in text
    assert "Dernier signal" not in text and "alertes envoyées" not in text
    assert len(text) < 320 and report == before


@pytest.mark.parametrize(
    "code,expected",
    [
        ("alerts_need_review", "Livraison d’alertes à vérifier"),
        ("no_enabled_sources", "Aucune source surveillée"),
        ("scan_invalid_timestamp", "Date du dernier cycle incohérente"),
        ("future_check", "Un contrôle du radar demande une vérification"),
    ],
)
def test_non_source_issues_are_not_hidden(report, code, expected):
    report["health"]["issues"] = [{"code": code, "source": None}]
    assert expected in format_incident_notice(report)
    assert format_incident_notice(report).startswith("⚠️")


def test_database_and_watcher_failure_never_claim_recovery(report):
    report["health"]["database"]["status"] = "unreadable"
    report["health"]["issues"] = [{"code": "database_unreadable", "source": None}]
    report["watcher"]["status"] = "stale"
    text = format_incident_notice(report)
    assert "Base locale inaccessible" in text and "Collecteur sans signal récent" in text
    assert "40/40" not in text and "✅" not in text


def test_many_problems_are_bounded_and_do_not_expose_raw_errors(report):
    for source in report["health"]["sources"]:
        source.update(
            company="🚀" * 1000,
            status="recent_failure",
            failure={"label": "⚠️" * 1000, "raw": "SECRET"},
        )
    for formatter in (format_incident_notice, format_status):
        text = formatter(report)
        assert len(text.encode("utf-16-le")) // 2 < 4096
        assert "autres sources ·" in text and "SECRET" not in text
