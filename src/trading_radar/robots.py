"""Bounded compatibility fix for Protego 0.6.2's terminal ``?$`` rules.

Protego drops the empty query separator before the end anchor (``*?$`` becomes
``*$``). Keep its group selection, precedence and linear wildcard matcher. The
private API use is isolated here and covered by HTTP-level regression tests.
"""

import re
from uuid import uuid4

from protego import Protego
from protego._urlpattern import _URLPattern
from protego._utils import _quote_path, _quote_pattern


class RobotsPolicy(Protego):
    def _parse_robotstxt(self, content: str) -> None:
        # Unique within this document, so an actual rule cannot be mistaken for
        # a placeholder. Let Protego itself handle grouping and directive syntax.
        prefix = f"/__radar_empty_query_rule_{uuid4().hex}_"
        while prefix in content:
            prefix += "_"
        replacements: dict[str, str] = {}
        lines = []
        for line in content.splitlines():
            directive = line.split("#", 1)[0].strip()
            match = re.fullmatch(r"(allow|disallow)\s*:\s*(.+\?\$)", directive, re.I)
            if match and match[2].count("?") == 1:
                marker = f"{prefix}{len(replacements)}__"
                replacements[marker] = match[2]
                line = f"{match[1]}: {marker}"
            lines.append(line)
        super()._parse_robotstxt("\n".join(lines))
        for ruleset in self._user_agents.values():
            corrected = []
            for rule in ruleset._rules:
                pattern = replacements.get(rule.value._pattern)
                if pattern is None:
                    corrected.append(rule)
                    continue
                # Quote before appending the anchor to preserve the literal '?'.
                corrected.append(
                    rule._replace(value=_URLPattern(_quote_pattern(pattern[:-1]) + "$"))
                )
                # Preserve Protego's additional interpretation of literal dollars.
                corrected.append(
                    rule._replace(value=_URLPattern(_quote_pattern(pattern.replace("$", "%24"))))
                )
            ruleset._rules = corrected
            ruleset.finalize_rules()

    def can_fetch(self, url: str, user_agent: str) -> bool:
        ruleset = self._get_matching_rule_set(user_agent)
        if ruleset is None:
            return True
        # A fragment is not sent to the server. urlparse otherwise loses a final
        # empty query delimiter, even though HTTPX preserves it on the wire.
        target = url.split("#", 1)[0]
        path = _quote_path(target)
        if target.endswith("?") and "?" not in path:
            path += "?"
        for rule in ruleset._rules:
            if rule.value.match(path):
                return rule.field == "allow"
        return True
