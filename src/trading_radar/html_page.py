"""Small non-executing HTML tree used by public career page parsers."""

from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    children: list["Element | str"] = field(default_factory=list)

    def text(self, without_headings: bool = False) -> str:
        if without_headings and self.tag in {"h1", "h2", "h3", "h4", "h5", "h6", "script", "style"}:
            return ""
        return " ".join(
            child.text(without_headings) if isinstance(child, Element) else child
            for child in self.children
        )

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.walk()


class Document(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.root = Element("root", {})
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def clean(node: Element) -> str:
    return " ".join(node.text().split())


def with_class(nodes, name: str) -> list[Element]:
    return [n for n in nodes if name in n.attrs.get("class", "").split()]
