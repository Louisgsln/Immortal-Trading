"""Preserve audited Optiver paragraphs and lists, without page code or links."""

import html
import re

from trading_radar.description_sections import normalize_heading, visible_text
from trading_radar.html_page import Element

_TAGS = {
    "p",
    "div",
    "section",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "i",
    "br",
}
_START = {"what you'll do", "what you' ll do"}
_END = {"what you'll get", "what you' ll get", "who you are", "what you'll need", "who we are"}


def _hidden(node: Element) -> bool:
    return (
        node.tag in {"script", "style", "template", "noscript", "iframe", "form"}
        or "hidden" in node.attrs
        or node.attrs.get("aria-hidden", "").lower() == "true"
        or bool(
            re.search(
                r"(?:display\s*:\s*none|visibility\s*:\s*hidden)\b",
                node.attrs.get("style", ""),
                re.I,
            )
        )
    )


def description_html(node: Element) -> str:
    """Keep structure and complete text in the one verified description block."""
    if _hidden(node):
        # Dropping hidden content must not connect a heading to an unrelated list.
        return "<span hidden></span>"
    content = " ".join(
        description_html(child) if isinstance(child, Element) else html.escape(child)
        for child in node.children
    )
    if node.tag == "br":
        return "<br>"
    # Unknown wrappers retain a boundary; links/images carry no URLs or attributes.
    tag = node.tag if node.tag in _TAGS else "span"
    return f"<{tag}>{content}</{tag}>"


def mission_section(root: Element) -> tuple[str, list[str]] | None:
    """One exact section, ending at an audited sibling heading.

    An optional introductory paragraph stays attached to the first list item.
    Unknown headings, intervening blocks or text after a list are ambiguous.
    """
    starts: list[tuple[Element, int]] = []

    def visit(node: Element) -> None:
        if _hidden(node):
            return
        for index, child in enumerate(node.children):
            if isinstance(child, Element) and not _hidden(child):
                if (
                    child.tag in {"p", "h2", "h3", "h4"}
                    and normalize_heading(visible_text(child)) in _START
                ):
                    starts.append((node, index))
                visit(child)

    visit(root)
    if len(starts) != 1:
        return None
    parent, start = starts[0]
    heading = parent.children[start]
    assert isinstance(heading, Element)
    intro: list[str] = []
    items: list[str] = []
    for child in parent.children[start + 1 :]:
        if isinstance(child, str):
            if child.strip():
                return None
            continue
        if _hidden(child):
            return None
        text = " ".join(visible_text(child).split())
        label = normalize_heading(text)
        if child.tag in {"p", "h2", "h3", "h4"} and label in _END:
            if not items:
                return None
            items[0] = " ".join([*intro, items[0]])
            return visible_text(heading), items
        bold = " ".join(visible_text(n) for n in child.walk() if n.tag in {"strong", "b"})
        if child.tag in {"h2", "h3", "h4", "h5", "h6"} or text and text == " ".join(bold.split()):
            return None
        if not text:
            continue
        if child.tag == "p" and not items:
            intro.append(text)
        elif child.tag in {"ul", "ol"} and not items:
            for item in child.children:
                if isinstance(item, str) and not item.strip():
                    continue
                if (
                    not isinstance(item, Element)
                    or item.tag != "li"
                    or any(_hidden(n) for n in item.walk())
                ):
                    return None
                items.append(visible_text(item))
        else:
            return None
    return None
