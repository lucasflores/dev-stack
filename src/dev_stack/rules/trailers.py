"""Trailer validation rules for dev-stack commit messages.

TrailerPresenceRule (UC2) — requires all five trailers on agent-generated commits.
TrailerPathRule (UC3) — validates that Spec-Ref/Task-Ref trailer paths exist.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gitlint.rules import CommitRule, RuleViolation


def _parse_trailers(body_lines: list[str]) -> dict[str, str]:
    """Parse git-trailer-style key-value pairs from commit body lines.

    Trailers appear at the end of the message body in ``Key: value`` format.
    """
    trailers: dict[str, str] = {}
    for line in reversed(body_lines):
        stripped = line.strip()
        if not stripped:
            break  # blank line ends trailer block
        if ": " in stripped:
            key, _, value = stripped.partition(": ")
            trailers[key.strip()] = value.strip()
        else:
            break
    return trailers


def _get_repo_root() -> Path | None:
    """Detect the git repository root via ``git rev-parse``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


class TrailerPresenceRule(CommitRule):
    """Require all five trailers on agent-generated commits (UC2).

    If the commit body contains an ``Agent:`` trailer, all of the following
    trailers are required: ``Spec-Ref``, ``Task-Ref``, ``Agent``,
    ``Pipeline``, ``Edited``.  Manual commits (no ``Agent:`` trailer) are
    not checked.
    """

    name = "dev-stack-trailer-presence"
    id = "UC2"

    REQUIRED_TRAILERS: tuple[str, ...] = (
        "Spec-Ref",
        "Task-Ref",
        "Agent",
        "Pipeline",
        "Edited",
    )

    def validate(self, commit):  # type: ignore[override]
        body_lines = commit.message.body if commit.message.body else []
        trailers = _parse_trailers(body_lines)

        # Only enforce on agent-generated commits
        if "Agent" not in trailers:
            return []

        violations: list[RuleViolation] = []
        for trailer_name in self.REQUIRED_TRAILERS:
            if trailer_name not in trailers:
                violations.append(
                    RuleViolation(
                        self.id,
                        f"Missing required trailer '{trailer_name}' on agent-generated commit. "
                        f"Agent commits must include: {', '.join(self.REQUIRED_TRAILERS)}",
                        line_nr=1,
                    )
                )
        return violations


class TrailerPathRule(CommitRule):
    """Validate Spec-Ref and Task-Ref trailer paths exist (UC3).

    Checks that paths referenced in ``Spec-Ref`` and ``Task-Ref`` trailers
    exist relative to the repository root.
    """

    name = "dev-stack-trailer-path"
    id = "UC3"

    PATH_TRAILERS: tuple[str, ...] = ("Spec-Ref", "Task-Ref")

    def validate(self, commit):  # type: ignore[override]
        body_lines = commit.message.body if commit.message.body else []
        trailers = _parse_trailers(body_lines)

        repo_root = _get_repo_root()
        if repo_root is None:
            return []  # Can't validate paths without repo root

        violations: list[RuleViolation] = []
        for trailer_name in self.PATH_TRAILERS:
            if trailer_name in trailers:
                ref_path = trailers[trailer_name]
                full_path = repo_root / ref_path
                if not full_path.exists():
                    violations.append(
                        RuleViolation(
                            self.id,
                            f"Trailer '{trailer_name}' references non-existent path: "
                            f"{ref_path} (resolved to {full_path})",
                            line_nr=1,
                        )
                    )
        return violations
