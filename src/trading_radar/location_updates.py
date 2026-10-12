"""Compare verified HSBC address sets without treating display order as a move."""

from trading_radar.models import Job
from trading_radar.normalizer import normalize_text


def hsbc_addresses(job: Job) -> list[str] | None:
    if job.source != "hsbc_graduates" or job.company_normalized != "hsbc":
        return None
    addresses = [part.strip() for part in job.location.split(";")]
    if len(addresses) < 2 or any(not part for part in addresses):
        return None
    return addresses


def location_change_key(job: Job) -> str | tuple[str, ...]:
    addresses = hsbc_addresses(job)
    if addresses is None:
        return job.location_normalized
    # Keep all address components: adding/removing a city or changing its region
    # or country remains a real change. Historical payloads need no migration.
    return tuple(sorted({normalize_text(part) for part in addresses}))


def location_label(job: Job) -> str:
    addresses = hsbc_addresses(job)
    if addresses is not None:
        components = [address.split(",") for address in addresses]
        if all(len(parts) == 3 and parts[-1].strip() == "CN" for parts in components):
            cities = sorted({parts[0].strip() for parts in components}, key=normalize_text)
            return " · ".join([*cities, "Chine"])
        return "; ".join(sorted(set(addresses), key=normalize_text))
    return job.location_normalized or "Lieu non précisé"
