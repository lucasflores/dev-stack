"""ConventionalCommitRule (UC1) — validates commit subject format.

Enforces the ``type(scope): description`` pattern per the Conventional Commits
specification.  Recognized types: feat, fix, docs, style, refactor, perf,
test, build, ci, chore, revert.
"""
from __future__ import annotations

import re

from gitlint.rules import CommitRule, RuleViolation


class ConventionalCommitRule(CommitRule):
    """Validate commit message subject matches conventional commit format.

    Rule ID ``UC1`` (User CommitRule 1).
    """

    name = "dev-stack-conventional-commit"
    id = "UC1"

    TYPES: tuple[str, ...] = (
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
    )

    PATTERN: re.Pattern[str] = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
        r"(\([a-z0-9_-]+\))?!?: .{1,72}$"
    )

    def validate(self, commit):  # type: ignore[override]
        """Return a list of violations if the subject is malformed."""
        title = commit.message.title

        if not self.PATTERN.match(title):
            allowed = ", ".join(self.TYPES)
            return [
                RuleViolation(
                    self.id,
                    f"Subject does not match conventional commit format. "
                    f"Expected: <type>(<scope>): <description> (max 72 chars). "
                    f"Allowed types: {allowed}",
                    title,
                )
            ]
        return []
