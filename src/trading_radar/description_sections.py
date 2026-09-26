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
        if child.tag in _HIDDEN or "hidden" in child.attrs:
            # A hidden list is not evidence, nor a bridge to an unlabelled list.
            previous = ""
            continue
        text = " ".join(visible_text(child).split())
        if child.tag in {"ul", "ol"} and normalize_heading(previous) in headings:
            yield previous, child
        if text:
            previous = text if child.tag in {"p", "h2", "h3", "h4", "strong"} else ""
        yield from labelled_lists(child, headings)


def bounded_paragraphs(root: Element, start: str, end: str) -> tuple[str, list[str]] | None:
    """One sibling section with both exact headings; keep complete paragraphs."""
    matches: list[tuple[str, list[str]]] = []
    labels: list[str] = []

    def visit(node: Element) -> None:
        if node.tag in _HIDDEN or "hidden" in node.attrs:
            return
        active: tuple[str, list[str]] | None = None
        for child in node.children:
            if isinstance(child, str):
                if child.strip():
                    active = None
                continue
            label = normalize_heading(visible_text(child))
            is_heading = child.tag in {"h2", "h3", "h4"}
            if is_heading and label in {start, end}:
                labels.append(label)
            if is_heading and label == end and active is not None:
                matches.append(active)
                active = None
            elif is_heading and label == start:
                active = (visible_text(child), [])
            elif active is not None:
                if child.tag == "p" and "hidden" not in child.attrs and visible_text(child).strip():
                    active[1].append(visible_text(child))
                else:
                    active = None
            visit(child)

    visit(root)
    return matches[0] if labels == [start, end] and len(matches) == 1 else None
