"""Visible employer conditions and material changes, without personal eligibility inference."""

import re

from trading_radar.deadlines import resolve_deadline
from trading_radar.description_sections import visible_text
from trading_radar.display_time import format_paris
from trading_radar.education import education_mentions
from trading_radar.experience import experience_requirement
from trading_radar.html_page import Document, Element
from trading_radar.models import Job
from trading_radar.normalizer import normalize_text
from trading_radar.start_dates import start_period


def deadline_label(job: Job) -> str:
    deadline = resolve_deadline(job)
    if deadline.precision == "conflict":
        return "à vérifier · indications contradictoires"
    if deadline.precision == "instant":
        return format_paris(deadline.instant, unknown="non précisée")
    if deadline.precision == "date" and deadline.day is not None:
        return deadline.day.strftime("%d/%m/%Y") + " · heure non précisée"
    return "non précisée"


def start_label(job: Job) -> str:
    period = start_period(job)
    if period["precision"] == "conflict":
        return "à vérifier · indications contradictoires"
    if job.expected_start_date:
        return job.expected_start_date
    if period["precision"] in {"year", "months"} and period["evidence"]:
        return period["evidence"][0]
    return "non précisé"


AUTHORIZATION = re.compile(
    r"\b(?:visa|visas|work authori[sz]ation|"
    r"authori[sz]ed to work|right to work|eligible to work|autorisation de travail|"
    r"droit de travailler|permis de travail)\b",
    re.I,
)


def authorization_evidence(job: Job) -> list[str]:
    root = Document(job.description).root
    blocks: list[str] = []

    def visit(node: Element) -> None:
        if not visible_text(node).strip():
            return
        if node.tag in {"p", "li"} and not any(
            isinstance(child, Element) and child.tag in {"p", "li"}
            for child in node.walk()
            if child is not node
        ):
            blocks.append(visible_text(node))
            return
        for child in node.children:
            if isinstance(child, Element):
                visit(child)

    visit(root)
    if not blocks:
        blocks = [visible_text(root)]
    evidence = []
    for block in blocks:
        for sentence in re.split(r"(?<=[.!?])\s+|[\n\r]+", block):
            sentence = " ".join(sentence.split())
            sponsoring_role = re.search(
                r"\bsponsor(?:ship|ing|ed)?\b", sentence, re.I
            ) and re.search(
                r"\b(?:candidate|applicant|role|position|employment|work permit|immigration)\b",
                sentence,
                re.I,
            )
            if AUTHORIZATION.search(sentence) or sponsoring_role:
                evidence.append(sentence)
    return list(dict.fromkeys(evidence))


def conditions(job: Job) -> dict:
    return {
        "start": start_period(job),
        "authorization": {"evidence": authorization_evidence(job)},
        "experience": experience_requirement(job),
        "education": education_mentions(job),
        "employment_type": job.employment_type,
    }


def material_changes(old: Job, new: Job, min_score: int = 70) -> list[str]:
    changes = []
    for field, label in [
        ("title_normalized", "Intitulé"),
        ("location_normalized", "Localisation"),
        ("application_deadline", "Échéance"),
        ("employment_type", "Contrat"),
    ]:
        if getattr(old, field) != getattr(new, field):
            changes.append(label)
    before, after = conditions(old), conditions(new)
    # A spelling/presentation change alone is not a new condition.
    start_before = {k: v for k, v in before["start"].items() if k != "evidence"}
    start_after = {k: v for k, v in after["start"].items() if k != "evidence"}
    if start_before != start_after or (
        start_before["precision"] == start_after["precision"] == "unknown"
        and normalize_text(old.expected_start_date or "")
        != normalize_text(new.expected_start_date or "")
    ):
        changes.append("Date de début")
    previous_deadline, current_deadline = resolve_deadline(old), resolve_deadline(new)
    if (previous_deadline.precision, previous_deadline.day, previous_deadline.instant) != (
        current_deadline.precision,
        current_deadline.day,
        current_deadline.instant,
    ) and "Échéance" not in changes:
        changes.append("Échéance")
    for key, label in [("authorization", "Visa / droit au travail"), ("education", "Diplôme")]:
        if key == "authorization":
            first = {normalize_text(item) for item in before[key]["evidence"]}
            second = {normalize_text(item) for item in after[key]["evidence"]}
        else:
            first = {normalize_text(item["excerpt"]) for item in before[key].get("evidence", [])}
            second = {normalize_text(item["excerpt"]) for item in after[key].get("evidence", [])}
        if first != second:
            changes.append(label)
    if before["experience"]["minimum_years"] != after["experience"]["minimum_years"]:
        changes.append("Expérience requise")
    if old.score_breakdown.total < min_score <= new.score_breakdown.total:
        changes.append("Devient prioritaire")
    return changes
