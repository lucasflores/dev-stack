"""Scope advisory — detect multi-concern changes.

Provides :func:`check_scope` which inspects staged file lists for
breadth indicators (FR-044, FR-045, FR-046).

The scope advisory is **always** non-blocking (informational only).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(slots=True)
class ScopeAdvisory:
    """Result of scope advisory analysis."""

    triggered: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        """Return ``"warn"`` if triggered, ``"pass"`` otherwise."""
        return "warn" if self.triggered else "pass"


def check_scope(staged_files: list[str]) -> ScopeAdvisory:
    """Analyse staged files for multi-concern breadth.

    **Trigger rules** (independent — any one fires ``triggered=True``):

    1. **Root directories**: 3+ distinct top-level directories
       (e.g., ``src/``, ``tests/``, ``specs/``).
    2. **Source subpackages**: 3+ distinct subpackages under the
       main ``src/<pkg>/`` package directory.
    3. **Specs+src overlap**: Changes touch both ``specs/`` and
       ``src/``.

    Args:
        staged_files: Relative file paths from ``git diff --cached --name-only``.

    Returns:
        :class:`ScopeAdvisory` — ``triggered`` is ``True`` if any rule fires;
        ``reasons`` lists human-readable explanations.
    """
    if not staged_files:
        return ScopeAdvisory()

    reasons: list[str] = []

    # Normalise paths and extract top-level directories
    root_dirs: set[str] = set()
    src_subpkgs: set[str] = set()
    has_specs = False
    has_src = False

    for raw in staged_files:
        parts = PurePosixPath(raw).parts
        if not parts:
            continue

        top = parts[0]
        root_dirs.add(top)

        if top == "specs":
            has_specs = True
        if top == "src":
            has_src = True

        # Detect source subpackages: src/<pkg>/<subpkg>/...
        if top == "src" and len(parts) >= 3:
            src_subpkgs.add(parts[2])

    # Rule 1: 3+ root directories
    if len(root_dirs) >= 3:
        reasons.append(
            f"Changes span {len(root_dirs)} root directories: {', '.join(sorted(root_dirs))}"
        )

    # Rule 2: 3+ source subpackages
    if len(src_subpkgs) >= 3:
        reasons.append(
            f"Changes span {len(src_subpkgs)} source subpackages: {', '.join(sorted(src_subpkgs))}"
        )

    # Rule 3: specs + src overlap
    if has_specs and has_src:
        reasons.append("Changes touch both specs/ and src/")

    return ScopeAdvisory(triggered=bool(reasons), reasons=reasons)
