"""Small private job lists from validated local observations, without writes."""

from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Literal

from trading_radar.audit import timestamp
from trading_radar.config import Config
from trading_radar.dashboard_data import DashboardDataError, read_jobs
from trading_radar.display_time import PARIS, format_paris
from trading_radar.health import check_health
from trading_radar.models import utcnow

REVIEW_STATUSES = {"New", "Reviewing", "To Apply"}


def units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if units(text) <= limit:
        return text
    return text.encode("utf-16-le")[: (limit - 1) * 2].decode("utf-16-le", errors="ignore") + "…"


def eligible(job: dict, sources: set[str], threshold: int, now: datetime) -> bool:
    first, last = timestamp(job["first_seen"]), timestamp(job["last_seen"])
    if (
        not job["is_active"]
        or job["is_expired"]
        or job["score"] < max(1, threshold)
        or job["application"]["status"] not in REVIEW_STATUSES
        or job["source"] not in sources
        or first is None
        or last is None
        or not first <= last <= now
        or now - last > timedelta(hours=24)
    ):
        return False
    deadline = job["deadline"]
    if deadline["precision"] == "instant":
        instant = timestamp(deadline["instant"])
        return instant is not None and instant > now
    if deadline["precision"] == "date":
        return date.fromisoformat(deadline["day"]) >= now.astimezone(PARIS).date()
    return deadline["precision"] == "unknown"


def card(job: dict, number: int) -> str:
    experience = job["experience"]["minimum_years"]
    last, first = timestamp(job["last_seen"]), timestamp(job["first_seen"])
    assert last is not None and first is not None
    lines = [
        f"{number}. {short(job['company'], 60)} — {job['score']}/100",
        short(job["title"], 140),
        short(job["location"] or "Lieu non précisé", 80),
        "Expérience : "
        + (f"minimum reconnu {experience} an(s)" if experience is not None else "minimum inconnu"),
        "Découverte : " + format_paris(first),
        "Vérifiée : " + format_paris(last),
    ]
    deadline = job["deadline"]
    if deadline["precision"] == "instant":
        instant = timestamp(deadline["instant"])
        assert instant is not None
        lines.append("Échéance : " + format_paris(instant))
    elif deadline["precision"] == "date":
        lines.append(f"Échéance : {deadline['day']} (heure/fuseau inconnus)")
    else:
        lines.append("Échéance : non précisée")
    url = job["apply_url"] or job["source_url"]
    # Never cut a URL into a plausible but broken application link.
    lines.append(
        url
        if url and units(url) <= 700
        else "Lien indisponible ici : consulter le dashboard local."
    )
    return "\n".join(lines)


def digest_card(job: dict, number: int | None = None) -> str:
    """A compact HTML card; preserve employer facts and complete safe links."""
    prefix = f"{number}. " if number is not None else ""
    lines = [
        f"{prefix}<b>{escape(short(job['company'], 60))}</b> · {job['score']}/100",
        escape(short(job["title"], 140)),
    ]
    location = job["location"] or "Lieu non précisé"
    parts = [part.strip() for part in location.split(",")]
    countries = job.get("location_facts", {}).get("countries", [])
    # This published hierarchy is city, continent, country, administrative area.
    # Other shapes may list several cities: retain them rather than guessing one.
    if (
        len(parts) >= 3
        and parts[1].casefold()
        in {"europe", "asia", "africa", "oceania", "north america", "south america"}
        and len(countries) == 1
    ):
        location = parts[0] + " · " + countries[0]["label"]
    lines.append("📍 " + escape(short(location, 100)))
    experience = job["experience"]["minimum_years"]
    if experience is not None:
        lines.append(f"Expérience min. : {experience} {'an' if experience <= 1 else 'ans'}")
    deadline = job["deadline"]
    if deadline["precision"] == "instant":
        instant = timestamp(deadline["instant"])
        assert instant is not None
        lines.append("⏳ Date limite : " + format_paris(instant) + " (Paris)")
    elif deadline["precision"] == "date":
        lines.append(
            "⏳ Date limite : "
            + date.fromisoformat(deadline["day"]).strftime("%d/%m/%Y")
            + " (heure non précisée)"
        )
    url = job["apply_url"] or job["source_url"]
    lines.append(
        f'<a href="{escape(url, quote=True)}">Voir l’offre ↗</a>'
        if url and units(url) <= 700
        else "Lien indisponible · consulter le Dashboard."
    )
    return "\n".join(lines)


def compact_digest(selected: list[dict], health: dict, instant: datetime, max_units: int) -> str:
    heading = "<b>🗓 Votre veille du jour</b>\n" + format_paris(instant)
    fresh = health["source_summary"].get("fresh", 0)
    footer = f"📡 Sources à jour : {fresh}/{len(health['sources'])} · /status"
    blocks: list[str] = []
    for index, job in enumerate(selected[:5], 1):
        block = digest_card(job, index if len(selected) > 1 else None)
        candidate = heading + "\n\n" + "\n\n".join([*blocks, block]) + "\n\n" + footer
        # Bound the HTML payload too, reserving the count and preview caption.
        if units(candidate) > max_units - 100:
            break
        blocks.append(block)
    total, shown = len(selected), len(blocks)
    count = f"{total} {'offre repérée' if total == 1 else 'offres repérées'} en 24 h"
    if shown < total:
        count += f" · {shown} {'affichée' if shown == 1 else 'affichées'}"
    body = "\n\n".join(blocks) if blocks else "Aucune offre vérifiée à vous proposer aujourd’hui."
    return heading + "\n<b>" + count + "</b>\n\n" + body + "\n\n" + footer


def jobs_message(
    config: Config,
    mode: Literal["top", "new"],
    now: datetime | None = None,
    *,
    max_units: int = 4000,
    compact: bool = False,
) -> str:
    instant = now or utcnow()
    if instant.tzinfo is None:
        raise ValueError("Telegram list time must have a timezone")
    instant = instant.astimezone(UTC)
    if mode not in {"top", "new"}:
        raise ValueError("Unknown job list")
    if not 2000 <= max_units <= 4000:
        raise ValueError("Invalid message budget")
    try:
        jobs = read_jobs(config)
    except DashboardDataError:
        return "📋 Offres indisponibles : la base locale ne peut pas être consultée. Réessaie plus tard ou consulte /status."
    health = check_health(config, now=instant)
    if health["database"]["status"] != "ok":
        return "📋 Offres indisponibles : la fraîcheur des sources ne peut pas être vérifiée. Consulte /status."
    sources = {s["source"] for s in health["sources"] if s["status"] == "fresh"}
    threshold = max(1, config.settings.alert_min_score)
    selected = [job for job in jobs if eligible(job, sources, threshold, instant)]
    if mode == "new":
        selected = [
            job
            for job in selected
            if instant - datetime.fromisoformat(job["first_seen"]) <= timedelta(hours=24)
        ]
        selected.sort(
            key=lambda j: (
                -datetime.fromisoformat(j["first_seen"]).timestamp(),
                -j["score"],
                j["id"],
            )
        )
    else:
        selected.sort(
            key=lambda j: (
                -j["score"],
                -datetime.fromisoformat(j["first_seen"]).timestamp(),
                j["id"],
            )
        )
    if compact:
        return compact_digest(selected, health, instant, max_units)
    title = "🏆 OFFRES À EXAMINER" if mode == "top" else "🆕 DÉCOUVERTES DEPUIS 24 H"
    header = f"{title}\nAu {format_paris(instant)} · score ≥ {threshold}/100"
    footer = (
        "Sources et fiches vérifiées depuis 24 h ; offres actives, à examiner. "
        "Candidatures déjà envoyées et échéances dépassées/ambiguës exclues.\n"
        "Découverte par le radar ≠ date de publication. Confirme les conditions sur le site employeur."
    )
    if len(sources) < len(health["sources"]):
        footer += "\nSources en échec ou anciennes écartées : /status."
    blocks: list[str] = []
    for job in selected[:5]:
        block = card(job, len(blocks) + 1)
        # Reserve space for the final count; send one complete message per command.
        candidate = header + "\n\n" + "\n\n".join([*blocks, block]) + "\n\n" + footer
        if units(candidate) > max_units - 100:
            break
        blocks.append(block)
    count = f"{len(blocks)} affichée(s) sur {len(selected)} correspondance(s)."
    body = (
        "\n\n".join(blocks) if blocks else "Aucune offre ne correspond actuellement à ces critères."
    )
    return header + "\n" + count + "\n\n" + body + "\n\n" + footer
