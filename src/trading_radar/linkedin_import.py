"""Owner-pasted LinkedIn vacancies; no scraping, login, or automatic verification."""

import html
import re
import unicodedata
from urllib.parse import urlsplit

from filelock import FileLock

from trading_radar.config import Config
from trading_radar.models import Job, RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.storage import Repository

SOURCE = "linkedin_manual"
USAGE = (
    "🔗 Ajouter une annonce LinkedIn\n\n"
    "Copie ce modèle dans un seul message :\n"
    "/linkedin\n"
    "Entreprise: Bank of America\n"
    "Poste: Global Markets Off-Cycle Analyst\n"
    "Lieu: Milan, Italie\n"
    "Lien: https://www.linkedin.com/jobs/view/1234567890/\n"
    "Description: colle ici le texte complet de l’annonce\n\n"
    "Import manuel, sans collecte automatique LinkedIn. Les informations absentes restent à vérifier."
)


class ImportRejected(ValueError):
    """A safe explanation, never the submitted text or a database error."""


def posting_url(value: str) -> tuple[str, str]:
    try:
        parts = urlsplit(value)
        match = re.fullmatch(r"/jobs/view/(?:[\w-]+-)?([1-9][0-9]{5,19})/?", parts.path)
        valid = (
            parts.scheme == "https"
            and bool(re.fullmatch(r"(?:(?:www|[a-z]{2})\.)?linkedin\.com", parts.netloc))
            and not parts.fragment
            and match is not None
            and not any(c.isspace() or unicodedata.category(c)[0] == "C" for c in value)
            and "\\" not in value
            and len(value) <= 2000
        )
    except ValueError:
        valid, match = False, None
    if not valid or match is None:
        raise ImportRejected(
            "Utilise le lien HTTPS d’une annonce LinkedIn avec son numéro d’offre."
        )
    identifier = match[1]
    return f"https://www.linkedin.com/jobs/view/{identifier}", identifier


def parse_offer(body: str) -> RawJob:
    if not isinstance(body, str) or not 1 <= len(body) <= 12000:
        raise ImportRejected("Le message d’import est vide ou trop long.")
    if any(unicodedata.category(c)[0] == "C" and c not in "\n\r\t" for c in body):
        raise ImportRejected("Le message contient des caractères non pris en charge.")
    aliases = {
        "entreprise": "company",
        "company": "company",
        "poste": "title",
        "titre": "title",
        "title": "title",
        "lieu": "location",
        "location": "location",
        "lien": "url",
        "url": "url",
        "description": "description",
    }
    fields: dict[str, str] = {}
    lines = body.strip().splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        name, separator, value = line.partition(":")
        key = aliases.get(name.strip().casefold())
        if not separator or key is None or key in fields:
            raise ImportRejected("Respecte le modèle : Entreprise, Poste, Lieu, Lien, Description.")
        if key == "description":
            fields[key] = "\n".join([value.strip(), *lines[index + 1 :]]).strip()
            break
        value = value.strip()
        if not value or len(value) > (2000 if key == "url" else 250):
            raise ImportRejected("Entreprise, poste, lieu ou lien manquant ou trop long.")
        fields[key] = value
    if not {"company", "title", "location", "url"} <= fields.keys():
        raise ImportRejected("Renseigne au minimum Entreprise, Poste, Lieu et Lien.")
    url, identifier = posting_url(fields["url"])
    description = "\n".join(
        "<p>" + html.escape(line) + "</p>"
        for line in fields.get("description", "").splitlines()
        if line.strip()
    )
    return RawJob(
        company=fields["company"],
        title=fields["title"],
        location=fields["location"],
        apply_url=url,
        source_url=url,
        external_id=identifier,
        source=SOURCE,
        source_type="aggregator",
        description=description,
    )


def import_offer(config: Config, body: str) -> tuple[Job, bool]:
    incoming = score_job(normalize(parse_offer(body)), config.keywords, settings=config.settings)
    repo = Repository(config.settings.database_url, existing_only=True)
    try:
        with FileLock(repo.lock_path, timeout=1), repo.transaction():
            identities = repo.db.execute(
                "SELECT j.payload FROM job_sources s JOIN jobs j ON j.id=s.job_id "
                "WHERE s.source=? AND s.external_id=?",
                (SOURCE, incoming.external_id),
            ).fetchall()
            if len(identities) > 1:
                raise ImportRejected("Cette référence est ambiguë. Consulte le Dashboard.")
            existing = (
                Job.model_validate_json(identities[0][0])
                if identities
                else repo.match_candidate(incoming)
            )
            if (
                identities
                and existing
                and existing.company_normalized != incoming.company_normalized
            ):
                raise ImportRejected("Cette référence LinkedIn est déjà liée à un autre employeur.")
            # A pasted advert cannot refresh, reopen or replace an employer-verified
            # record. Repeated imports also keep the user's tracking and observations.
            if existing:
                return existing, False
            job, _ = repo.upsert(incoming)
            # A manual observation can be bookmarked, but must never keep a
            # later employer-verified offer open after its official withdrawal.
            repo.db.execute(
                "UPDATE job_sources SET is_active=0 WHERE source=? AND job_id=?",
                (SOURCE, job.id),
            )
            return job, True
    finally:
        repo.close()
