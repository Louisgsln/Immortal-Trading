"""Reviewed Old Mission duties connecting research to options and trading decisions."""

import html

from trading_radar.description_sections import labelled_lists, visible_text
from trading_radar.html_page import Document, Element
from trading_radar.normalizer import has, normalize_text


def research_duties(title: str, description: str) -> bool:
    title = normalize_text(title)
    fundamental = title.startswith("fundamental research analyst")
    quantitative = title.startswith("quantitative researcher")
    if not (fundamental or quantitative):
        return False
    sections = list(labelled_lists(Document(html.unescape(description)).root, {"responsibilities"}))
    if len(sections) != 1:
        return False
    duties = [
        normalize_text(visible_text(item))
        for item in sections[0][1].children
        if isinstance(item, Element) and item.tag == "li"
    ]

    def duty(*terms: str) -> bool:
        return any(all(has(item, term) for term in terms) for item in duties)

    if fundamental:
        return duty("conduct quantitative and qualitative analysis", "trading decisions") and duty(
            "collaborate directly with traders", "fundamental overlay", "testing strategies"
        )
    return duty("conceptualize and implement", "derivative pricing models", "vix options") and duty(
        "collaborate closely with traders", "jointly developing new tools", "patterns in the market"
    )
