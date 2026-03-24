"""Body section validation rule for agent commits (UC5).

Requires ## Intent, ## Reasoning, ## Scope, ## Narrative headings
on commits that have an Agent: trailer. Human commits are not checked.
"""
from __future__ import annotations

from gitlint.rules import CommitRule, RuleViolation

from .trailers import _parse_trailers


class BodySectionRule(CommitRule):
    """Require body sections on agent-generated commits (UC5)."""

    name = "dev-stack-body-sections"
    id = "UC5"

    REQUIRED_SECTIONS: tuple[str, ...] = (
        "## Intent",
        "## Reasoning",
        "## Scope",
        "## Narrative",
    )

    def validate(self, commit):  # type: ignore[override]
        body_lines = commit.message.body if commit.message.body else []
        trailers = _parse_trailers(body_lines)

        if "Agent" not in trailers:
            return []

        body_text = "\n".join(body_lines)
        missing = [
            s for s in self.REQUIRED_SECTIONS
            if not any(line.rstrip() == s for line in body_lines)
        ]

        if not missing:
            return []

        return [
            RuleViolation(
                self.id,
                f"Agent commit missing required body sections: {', '.join(missing)}. "
                f"Agent commits must include: {', '.join(self.REQUIRED_SECTIONS)}",
                line_nr=1,
            )
        ]
