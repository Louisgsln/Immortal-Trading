"""Small private job lists from validated local observations, without writes."""

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from trading_radar.audit import timestamp
from trading_radar.config import Config
from trading_radar.dashboard_data import DashboardDataError, read_jobs
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
        return date.fromisoformat(deadline["day"]) >= now.date()
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
        "Découverte : " + first.strftime("%d/%m %H:%M UTC"),
        "Vérifiée : " + last.strftime("%d/%m %H:%M UTC"),
    ]
    deadline = job["deadline"]
    if deadline["precision"] == "instant":
        instant = timestamp(deadline["instant"])
        assert instant is not None
        lines.append("Échéance : " + instant.strftime("%d/%m/%Y %H:%M UTC"))
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


def jobs_message(config: Config, mode: Literal["top", "new"], now: datetime | None = None) -> str:
    instant = now or utcnow()
    if instant.tzinfo is None:
        raise ValueError("Telegram list time must have a timezone")
    instant = instant.astimezone(UTC)
    if mode not in {"top", "new"}:
        raise ValueError("Unknown job list")
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
    title = "🏆 OFFRES À EXAMINER" if mode == "top" else "🆕 DÉCOUVERTES DEPUIS 24 H"
    header = f"{title}\nAu {instant:%d/%m/%Y %H:%M UTC} · score ≥ {threshold}/100"
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
        if units(candidate) > 3900:
            break
        blocks.append(block)
    count = f"{len(blocks)} affichée(s) sur {len(selected)} correspondance(s)."
    body = (
        "\n\n".join(blocks) if blocks else "Aucune offre ne correspond actuellement à ces critères."
    )
    return header + "\n" + count + "\n\n" + body + "\n\n" + footer
