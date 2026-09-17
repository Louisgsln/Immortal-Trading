"""Read-only experience observations for the dashboard, not eligibility decisions."""

from trading_radar.models import Job
from trading_radar.scoring import required_experience_years


def experience_requirement(job: Job) -> dict[str, int | str | None]:
    """Report the strongest recognized numeric minimum, including structured zero.

    Reuse the scoring parser's range and preference rules. An unspecified result
    means no numeric minimum was recognized; it does not mean no experience is
    required. Titles and junior/senior hints do not supply a numeric minimum.
    """
    minima = required_experience_years(job.description_text)
    structured = job.minimum_experience_years
    # Jobs normally arrive validated. Keep unvalidated copies or callers from
    # coercing unknown metadata, strings or booleans into an experience value.
    if type(structured) is int and 0 <= structured <= 99:
        minima.append(structured)
    minimum = max(minima) if minima else None
    return {
        "minimum_years": minimum,
        "category": "unspecified" if minimum is None else "up_to_2" if minimum <= 2 else "over_2",
    }
