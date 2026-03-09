"""Unit tests for ConventionalCommitRule (UC1).

Validates:
- Valid subjects with all 11 allowed types
- Optional scope, breaking change indicator
- Invalid subjects: wrong type, missing colon, oversized description
- Edge cases: empty title, just type prefix
"""
from __future__ import annotations

import pytest

from dev_stack.rules.conventional import ConventionalCommitRule


class FakeTitle:
    """Minimal stand-in for ``commit.message.title``."""

    def __init__(self, title: str) -> None:
        self._title = title

    def __str__(self) -> str:
        return self._title


class FakeMessage:
    def __init__(self, title: str) -> None:
        self.title = title


class FakeCommit:
    def __init__(self, title: str) -> None:
        self.message = FakeMessage(title)


@pytest.fixture
def rule() -> ConventionalCommitRule:
    return ConventionalCommitRule()


# ---- Valid subjects -------------------------------------------------------

VALID_SUBJECTS = [
    "feat: add new command",
    "fix: resolve crash on startup",
    "docs: update readme",
    "style: format code with ruff",
    "refactor: extract helper function",
    "perf: optimize query performance",
    "test: add unit tests for parser",
    "build: update dependencies",
    "ci: add github actions workflow",
    "chore: update changelog",
    "revert: revert commit abc123",
    "feat(cli): add --verbose flag",
    "fix(parser): handle empty input",
    "feat!: breaking change description",
    "feat(cli)!: breaking scoped change",
]


@pytest.mark.parametrize("subject", VALID_SUBJECTS)
def test_valid_subjects_produce_no_violations(rule: ConventionalCommitRule, subject: str) -> None:
    commit = FakeCommit(subject)
    violations = rule.validate(commit)
    assert violations == [], f"Unexpected violations for valid subject: {subject!r}"


# ---- Invalid subjects -----------------------------------------------------

INVALID_SUBJECTS = [
    ("Update readme", "no type prefix"),
    ("FEAT: uppercase type", "uppercase type"),
    ("feat:", "missing description"),
    ("feat:no space", "missing space after colon"),
    ("feature: too long type", "unknown type"),
    ("fix(SCOPE): uppercase scope", "uppercase scope"),
    ("", "empty title"),
    ("x" * 80, "oversized without type"),
    ("feat: " + "x" * 73, "description exceeds 72 char limit"),
]


@pytest.mark.parametrize("subject,reason", INVALID_SUBJECTS)
def test_invalid_subjects_produce_violations(
    rule: ConventionalCommitRule, subject: str, reason: str
) -> None:
    commit = FakeCommit(subject)
    violations = rule.validate(commit)
    assert len(violations) > 0, f"Expected violation for: {reason} ({subject!r})"
    assert violations[0].rule_id == "UC1"


# ---- All 11 types ---------------------------------------------------------

def test_all_eleven_types_accepted(rule: ConventionalCommitRule) -> None:
    for commit_type in rule.TYPES:
        commit = FakeCommit(f"{commit_type}: valid description")
        violations = rule.validate(commit)
        assert violations == [], f"Type '{commit_type}' should be valid"


# ---- 72-char boundary -----------------------------------------------------

def test_description_exactly_72_chars_accepted(rule: ConventionalCommitRule) -> None:
    # The regex limits the description portion (after ': ') to 72 chars
    desc = "x" * 72
    commit = FakeCommit(f"feat: {desc}")
    violations = rule.validate(commit)
    assert violations == []


def test_description_over_72_chars_rejected(rule: ConventionalCommitRule) -> None:
    desc = "x" * 73
    commit = FakeCommit(f"feat: {desc}")
    violations = rule.validate(commit)
    assert len(violations) > 0


# ---- Scope validation -----------------------------------------------------

def test_scope_with_hyphens_accepted(rule: ConventionalCommitRule) -> None:
    commit = FakeCommit("feat(my-scope): description")
    assert rule.validate(commit) == []


def test_scope_with_underscores_accepted(rule: ConventionalCommitRule) -> None:
    commit = FakeCommit("feat(my_scope): description")
    assert rule.validate(commit) == []


def test_scope_with_numbers_accepted(rule: ConventionalCommitRule) -> None:
    commit = FakeCommit("feat(scope123): description")
    assert rule.validate(commit) == []
