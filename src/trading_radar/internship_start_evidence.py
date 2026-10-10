"""Audited conditional conversion dates, separate from the internship intake."""

from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document
from trading_radar.models import Job
from trading_radar.normalizer import normalize_text

BOFA_CONVERSION = (
    "Candidates who perform well during the internship may be offered full time employment "
    "to commence in July 2028; some lines of business may also offer the opportunity of a "
    "January or April start date. You must be available to join on one of these start dates "
    "if offered, unfortunately we are unable to offer deferrals."
)


def candidate_start_text(job: Job) -> str:
    document = Document(job.description)
    if (
        job.source == "bank_of_america_campus"
        and job.company == "Bank of America"
        and job.source_type == "official"
        and job.employment_type in {"Off-cycle internship", "Summer internship"}
    ):
        for node in document.root.walk():
            if node.tag in {"p", "li"} and normalize_text(visible_text(node)) in {
                normalize_text(BOFA_CONVERSION),
                normalize_text(BOFA_CONVERSION + " (Full time, off-cycle and IP)"),
                normalize_text(BOFA_CONVERSION.replace("July 2028", "July 2029")),
            }:
                # Only this reviewed conditional conversion paragraph is omitted
                # from start-period extraction. The stored description is intact.
                node.children = []
    text = visible_text(document.root)
    if (
        job.source == "deutsche_bank_campus"
        and job.company == "Deutsche Bank"
        and job.source_type == "official"
        and job.employment_type == "Analyst Internship Programme"
    ):
        # Reviewed 2027 UK eligibility describes the subsequent full-time job.
        # Remove only this exact conversion sentence from date extraction;
        # other years and the original stored description remain untouched.
        text = text.replace(
            "Be able to start full time work in July 2028, subject to local working legislation and visa requirements.",
            "",
        )
    return text
