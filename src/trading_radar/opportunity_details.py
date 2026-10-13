"""Evidence-backed display of the four employer fields, including unknowns."""

import re
from urllib.parse import urlsplit

from trading_radar.deadlines import LABEL as DEADLINE_LABEL
from trading_radar.deadlines import resolve_deadline
from trading_radar.description_sections import labelled_lists, normalize_heading, visible_text
from trading_radar.experience import experience_requirement
from trading_radar.html_page import Document, Element
from trading_radar.job_conditions import deadline_label, start_label
from trading_radar.location_updates import hsbc_addresses, location_label
from trading_radar.models import Job
from trading_radar.opportunity_facts import country_facts, start_facts
from trading_radar.ubs_sections import bullet_items, field_lines

PROFILE_HEADINGS = {
    "your skills and experience",
    "your expertise",
    "your profile",
    "votre profil",
    "profil recherché",
    "profil recherche",
    "qualifications",
    "requirements",
    "required qualifications",
    "preferred qualifications",
    "basic qualifications",
    "skills and experience",
    "what you bring",
    "what you bring to the team",
    "what we are looking for",
    "what you'll bring to the role",
    "what you will need",
    "essential skills/basic qualifications",
    "experience",
    "expérience",
    "required experience",
    "preferred experience",
    "key skills",
    "skills you'll need",
    "skills you will need",
    "who you are",
    "profile and skills to success",
    "technical and behavioral competencies",
    "your background",
    "about you",
    "candidate profile",
    "the successful candidate",
}
EXPERIENCE = re.compile(
    r"\b(?:(?:prior|previous|relevant|professional|proven|demonstrated|practical|"
    r"hands[- ]on|solid|strong|extensive|significant)\s+(?:(?!client\b|customer\b|user\b|focus\b|guest\b)[\w/-]+\s+){0,5}experience|"
    r"experience\s+(?:in|with|of|working|trading|building|developing)|"
    r"experienced\s+in|expérience\s+(?:en|dans|de|professionnelle|préalable|significative)|"
    r"première\s+expérience)\b",
    re.I,
)


def _profile_items(job: Job) -> list[str]:
    root = Document(job.description).root
    if job.source == "ubs_professionals" and job.company == "UBS":
        items = []
        for label in ("your skills and experience", "your expertise"):
            lines = field_lines(root, label, {"about us", "your career comeback", "the team"})
            items.extend(bullet_items(lines, mixed=True) or [] if lines is not None else [])
        return items
    items = []
    for heading, group in labelled_lists(root, PROFILE_HEADINGS):
        for child in group.children:
            if isinstance(child, Element) and child.tag == "li":
                items.append(heading + ": " + " ".join(visible_text(child).split()))

    # Also retain complete paragraphs under bounded candidate headings.
    def visit(node: Element):
        if node.tag in {"script", "style", "template", "noscript"} or "hidden" in node.attrs:
            return
        heading = None
        for child in node.children:
            if not isinstance(child, Element):
                continue
            if child.tag in {"h2", "h3", "h4"}:
                text = normalize_heading(visible_text(child))
                heading = text if text in PROFILE_HEADINGS else None
            elif heading and child.tag == "p":
                text = " ".join(visible_text(child).split())
                if text:
                    items.append(heading + ": " + text)
            visit(child)

    visit(root)
    return list(dict.fromkeys(items))


def experience_detail(job: Job) -> dict:
    observed = experience_requirement(job)
    minimum = observed["minimum_years"]
    if minimum is not None:
        evidence = [item["excerpt"] for item in observed.get("evidence", [])]
        return {
            "status": "numeric",
            "label": f"minimum reconnu : {minimum} an(s)",
            "minimum_years": minimum,
            "evidence": evidence,
        }
    items = [
        text
        for text in _profile_items(job)
        if EXPERIENCE.search(text)
        or re.search(
            r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s*\+?\s+(?:years?|ans?)\b[^.!?]{0,50}(?:experience|expérience)",
            text,
            re.I,
        )
    ]
    if items:
        label = (
            "« " + items[0][:180] + ("…" if len(items[0]) > 180 else "") + " » · durée non chiffrée"
        )
        if re.search(r"\b(?:years?|ans?)\b", items[0], re.I):
            label = (
                "« "
                + items[0][:180]
                + ("…" if len(items[0]) > 180 else "")
                + " » · minimum obligatoire non confirmé"
            )
        # Reviewed wording from the official UBS Crypto/eFX candidate section.
        if (
            job.source == "ubs_professionals"
            and job.company == "UBS"
            and re.search(
                r"prior experience.*DA native company.*(?:on an? )?eFX Trading desk", items[0], re.I
            )
        ):
            label = "Expérience préalable en actifs numériques ou desk eFX · durée non chiffrée"
        return {
            "status": "qualitative",
            "label": label,
            "minimum_years": None,
            "evidence": items[:5],
        }
    return {
        "status": "not_published",
        "label": "Minimum d’expérience non indiqué par l’employeur",
        "minimum_years": None,
        "evidence": [],
    }


def public_source_url(job: Job) -> str | None:
    for value in (job.source_url, job.apply_url):
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme in {"https", "http"}
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and len(value) <= 2000
                and not any(ord(char) < 33 for char in value)
            ):
                return value
        except ValueError:
            pass
    return None


def opportunity_details(job: Job) -> dict:
    location = country_facts(job)
    countries = location["countries"]
    if len(countries) == 1 and hsbc_addresses(job) is None:
        country = countries[0]
        place = " ".join(job.location.split()).strip()
        if job.city and (job.country or "").replace("UK", "GB") == country["code"]:
            place = job.city
        if country["code"] == "SG" and place.lower() in {
            "singapore",
            "singapore, singapore",
            "singapore, sg",
        }:
            place = "Singapour"
        location_text = (
            f"{place} · {country['label']} ({country['code']})"
            if place != country["label"]
            else f"{place} ({country['code']})"
        )
    else:
        location_text = location_label(job)
    deadline = resolve_deadline(job)
    start = start_facts(job)
    start_status = start["precision"]
    start_text = start_label(job)
    if start_status == "day":
        from datetime import date

        start_text = date.fromisoformat(start["windows"][0]["from"]).strftime("%d/%m/%Y")
    if start_status == "unknown":
        statements = start["evidence"]
        combined = " ".join(statements)
        if re.search(
            r"\b(?:ASAP|immediately|as soon as possible|dès que possible|des que possible)\b",
            combined,
            re.I,
        ):
            start_status = "qualitative"
            start_text = "Dès que possible · indiqué par l’employeur"
        elif re.search(r"\b(?:to be agreed|à convenir|a convenir)\b", combined, re.I):
            start_status = "qualitative"
            start_text = "À convenir · indiqué par l’employeur"
    if start_status == "unknown":
        start_text = "Date non indiquée par l’employeur"
        date_words = r"\b(?:January|February|March|April|June|July|August|September|October|November|December|janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\b|\b20\d{2}\b|\d{1,2}[/.-]\d{1,2}"
        if job.expected_start_date or re.search(date_words, " ".join(start["evidence"]), re.I):
            start_status = "unrecognized"
            start_text = "Début annoncé à vérifier · voir l’extrait employeur"
    if start_status == "year" and re.search(
        r"\b\d{1,2}/\d{1,2}/20\d{2}\b", " ".join(start["evidence"])
    ):
        start_status = "unrecognized"
        start_text = "Date annoncée ambiguë · consulter l’extrait"
    deadline_status = deadline.precision
    deadline_text = deadline_label(job)
    if deadline_status == "unknown":
        deadline_status = (
            "unrecognized" if DEADLINE_LABEL.search(job.description_text) else "not_published"
        )
        deadline_text = (
            "Échéance annoncée à vérifier · voir l’offre"
            if deadline_status == "unrecognized"
            else "Date non indiquée par l’employeur"
        )
    if deadline_status == "not_published" and re.search(
        r"\b(?:applications?|recruitment|candidatures?|recrutement)\b[^.!?]{0,100}(?:rolling basis|fil de l[’']eau)",
        job.description_text,
        re.I,
    ):
        deadline_status = "qualitative"
        deadline_text = "Recrutement au fil de l’eau · aucune date publiée"
    if deadline_status == "unrecognized":
        match = DEADLINE_LABEL.search(job.description_text)
        if match:
            snippet = re.split(
                r"(?<=[.!?])\s+",
                job.description_text[match.start() : match.end() + 180],
                maxsplit=1,
            )[0]
            deadline.evidence = [snippet]
            deadline_text = (
                "« "
                + snippet[:140]
                + ("…" if len(snippet) > 140 else "")
                + " » · date à interpréter"
            )
    return {
        "location": {
            "status": "recognized"
            if countries
            else "unrecognized"
            if job.location.strip()
            else "not_published",
            "label": location_text,
            "evidence": [job.location] if job.location else [],
            "countries": countries,
        },
        "start": {
            "status": "not_published" if start_status == "unknown" else start_status,
            "label": start_text,
            "evidence": start["evidence"],
        },
        "experience": experience_detail(job),
        "deadline": {
            "status": deadline_status,
            "label": deadline_text,
            "evidence": deadline.evidence,
        },
        "source_url": public_source_url(job),
        "verified_at": job.last_seen.isoformat(),
    }
