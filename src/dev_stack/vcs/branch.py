"""Branch name validation utilities.

Provides :func:`validate_branch_name` which checks a branch against
a configurable regex pattern and exempt list, returning structured
error/warning results.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class BranchValidationResult:
    """Outcome of a branch name validation check."""

    ok: bool
    """``True`` when the branch name is acceptable (pass or exempt)."""

    status: Literal["pass", "exempt", "fail", "warn"]
    """One of *pass*, *exempt*, *fail* (hard block), or *warn* (spec mismatch)."""

    message: str | None = None
    """Human-readable explanation (set on fail/warn)."""


def validate_branch_name(
    branch: str,
    *,
    pattern: str = (
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)/[a-z0-9._-]+$"
    ),
    exempt: list[str] | None = None,
    spec_branch: str | None = None,
) -> BranchValidationResult:
    """Validate *branch* against a naming pattern.

    Logic:
        1. If *branch* is in *exempt* list → ``exempt`` (always allowed).
        2. If *branch* does not match *pattern* → ``fail`` with error message.
        3. If *spec_branch* is given and differs from *branch* → ``warn`` (non-blocking).
        4. Otherwise → ``pass``.

    Args:
        branch: The local branch name (e.g. ``feat/my-feature``).
        pattern: Regex applied via :func:`re.fullmatch`.
        exempt: Branch names that bypass pattern validation.
            Defaults to ``["main", "master", "develop", "staging", "production"]``.
        spec_branch: Optional branch declared in an active spec file.
            When set, a non-blocking warning fires if *branch* ≠ *spec_branch*.

    Returns:
        :class:`BranchValidationResult` with verdict and optional message.
    """
    if exempt is None:
        exempt = ["main", "master", "develop", "staging", "production"]

    # 1. Exempt branches always pass.
    if branch in exempt:
        return BranchValidationResult(ok=True, status="exempt")

    # 2. Pattern match
    if not re.fullmatch(pattern, branch):
        return BranchValidationResult(
            ok=False,
            status="fail",
            message=(
                f"Branch '{branch}' does not match required pattern: {pattern}\n"
                f"Example: feat/my-feature, fix/issue-42, docs/readme-update"
            ),
        )

    # 3. Spec-branch mismatch warning (non-blocking)
    if spec_branch and branch != spec_branch:
        return BranchValidationResult(
            ok=True,
            status="warn",
            message=(
                f"Warning: current branch '{branch}' does not match "
                f"spec-declared branch '{spec_branch}'"
            ),
        )

    # 4. All good
    return BranchValidationResult(ok=True, status="pass")


def _detect_spec_branch(repo_root: Path) -> str | None:
    """Attempt to detect the feature branch from an active spec-kit spec.

    Scans ``specs/*/spec.md`` for a ``**Branch**: `xxx``` line.

    Returns:
        The declared branch name, or ``None`` if not found / not applicable.
    """
    specs_dir = repo_root / "specs"
    if not specs_dir.is_dir():
        return None

    # Walk in sorted order for determinism; take the first match
    for spec_dir in sorted(specs_dir.iterdir()):
        spec_file = spec_dir / "spec.md"
        if not spec_file.is_file():
            continue
        try:
            text = spec_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                # Pattern: **Branch**: `004-vcs-best-practices`
                m = re.search(r"\*\*Branch\*\*:\s*`([^`]+)`", line)
                if m:
                    return m.group(1)
        except OSError:
            continue

    return None
