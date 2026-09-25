"""Visible text and adjacent labelled lists in employer HTML descriptions."""

from collections.abc import Iterator

from trading_radar.html_page import Element

_HIDDEN = {"script", "style", "template", "noscript"}


def visible_text(node: Element) -> str:
    if node.tag in _HIDDEN or "hidden" in node.attrs:
        return ""
    return " ".join(
        visible_text(child) if isinstance(child, Element) else child for child in node.children
    )


def normalize_heading(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").replace("&", "and").split()).strip(" :.…")


def labelled_lists(node: Element, headings: set[str]) -> Iterator[tuple[str, Element]]:
    if node.tag in _HIDDEN or "hidden" in node.attrs:
        return
    previous = ""
    for child in node.children:
        if isinstance(child, str):
            if child.strip():
                previous = ""
            continue
        text = " ".join(visible_text(child).split())
        if child.tag in {"ul", "ol"} and normalize_heading(previous) in headings:
            yield previous, child
        if text:
            previous = text if child.tag in {"p", "h2", "h3", "h4", "strong"} else ""
        yield from labelled_lists(child, headings)
