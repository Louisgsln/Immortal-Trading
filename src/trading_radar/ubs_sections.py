"""Bounded UBS fields, retaining bullet continuations and qualification scope."""

from trading_radar.description_sections import normalize_heading, visible_text
from trading_radar.html_page import Element


def field_lines(root: Element, label: str, following: set[str]) -> list[str] | None:
    headings = [
        (i, node)
        for i, node in enumerate(root.children)
        if isinstance(node, Element) and node.tag == "h2"
    ]
    matches = [
        i for i, (_, node) in enumerate(headings) if normalize_heading(visible_text(node)) == label
    ]
    if len(matches) != 1:
        return None
    pos = matches[0]
    if (
        pos + 1 == len(headings)
        or normalize_heading(visible_text(headings[pos + 1][1])) not in following
    ):
        return None

    def inline(node: Element | str) -> str | None:
        if isinstance(node, str):
            return node
        if node.tag == "br" and "hidden" not in node.attrs:
            return "\n"
        if not visible_text(node).strip():
            return ""
        # Audited publishing marker, not a candidate requirement. Match the
        # entire element so a changed or meaningful white label is not dropped.
        if (
            node.tag == "font"
            and node.attrs == {"color": "white"}
            and visible_text(node).strip() == "*LI-GB"
        ):
            return ""
        if node.tag not in {"b", "strong", "span", "i", "em", "a", "font"}:
            return None
        parts = [inline(c) for c in node.children]
        return "".join(p for p in parts if p is not None) if None not in parts else None

    start, end = headings[pos][0], headings[pos + 1][0]
    parts = [inline(node) for node in root.children[start + 1 : end]]
    if None in parts:
        return None
    return [
        line.strip()
        for line in "".join(p for p in parts if p is not None).splitlines()
        if line.strip()
    ]


def bullet_items(lines: list[str], *, mixed: bool = False) -> list[str] | None:
    first = next((i for i, line in enumerate(lines) if line.startswith("•")), None)
    if first is None:
        return None
    preface = base = " ".join(lines[:first])
    groups = {"you are", "preferred skills", "personal attributes"}
    items: list[str] = []
    current = ""
    for line in lines[first:]:
        if line.startswith("•"):
            if not line[1:].strip():
                return None
            if current:
                items.append(" ".join((preface + " " + current).split()))
            current = line[1:].strip()
        elif mixed and normalize_heading(line) in groups:
            if not current:
                return None
            items.append(" ".join((preface + " " + current).split()))
            current = ""
            preface = " ".join((base + " " + line).split())
        elif mixed and line.startswith("o ") and current:
            current += " " + line
        else:
            return None
    if not current:
        return None
    items.append(" ".join((preface + " " + current).split()))
    return items
