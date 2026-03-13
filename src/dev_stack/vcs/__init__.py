"""VCS automation utilities for dev-stack.

Provides configuration loading, hook runners, branch validation,
signing utilities, PR description generation, changelog/release
automation, and scope advisory checks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(slots=True)
class HooksConfig:
    """Configuration for which git hooks to install."""

    commit_msg: bool = True
    pre_push: bool = True
    pre_commit: bool = True


@dataclass(slots=True)
class BranchConfig:
    """Configuration for branch naming enforcement."""

    pattern: str = (
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)/[a-z0-9._-]+$"
    )
    exempt: list[str] = field(
        default_factory=lambda: ["main", "master", "develop", "staging", "production"]
    )

    def __post_init__(self) -> None:
        # Validate that ``pattern`` compiles as a regex.
        re.compile(self.pattern)


@dataclass(slots=True)
class SigningConfig:
    """Configuration for SSH commit signing."""

    enabled: bool = False
    enforcement: str = "warn"  # "warn" or "block"
    key: str | None = None  # Path to SSH public key; auto-detected if None

    def __post_init__(self) -> None:
        if self.enforcement not in ("warn", "block"):
            raise ValueError(f"enforcement must be 'warn' or 'block', got '{self.enforcement}'")


@dataclass(slots=True)
class VcsConfig:
    """Aggregated VCS configuration read from pyproject.toml."""

    hooks: HooksConfig = field(default_factory=HooksConfig)
    branch: BranchConfig = field(default_factory=BranchConfig)
    signing: SigningConfig = field(default_factory=SigningConfig)


def load_vcs_config(repo_root: Path) -> VcsConfig:
    """Load VCS configuration from ``pyproject.toml``.

    Reads ``[tool.dev-stack.hooks]``, ``[tool.dev-stack.branch]``, and
    ``[tool.dev-stack.signing]`` sections.  Missing sections fall back to
    dataclass defaults.

    Args:
        repo_root: Repository root directory containing ``pyproject.toml``.

    Returns:
        :class:`VcsConfig` with merged defaults and user overrides.
    """
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return VcsConfig()

    with open(pyproject, "rb") as fh:
        data = tomllib.load(fh)

    ds: dict[str, Any] = data.get("tool", {}).get("dev-stack", {})

    # Create default instances for fallback values (slots=True prevents
    # class-level attribute access to defaults).
    _hooks_defaults = HooksConfig()
    _branch_defaults = BranchConfig()
    _signing_defaults = SigningConfig()

    # --- hooks ---
    hooks_raw = ds.get("hooks", {})
    hooks = HooksConfig(
        commit_msg=hooks_raw.get("commit-msg", _hooks_defaults.commit_msg),
        pre_push=hooks_raw.get("pre-push", _hooks_defaults.pre_push),
        pre_commit=hooks_raw.get("pre-commit", _hooks_defaults.pre_commit),
    )

    # --- branch ---
    branch_raw = ds.get("branch", {})
    branch = BranchConfig(
        pattern=branch_raw.get("pattern", _branch_defaults.pattern),
        exempt=branch_raw.get("exempt", _branch_defaults.exempt),
    )

    # --- signing ---
    signing_raw = ds.get("signing", {})
    signing = SigningConfig(
        enabled=signing_raw.get("enabled", _signing_defaults.enabled),
        enforcement=signing_raw.get("enforcement", _signing_defaults.enforcement),
        key=signing_raw.get("key", _signing_defaults.key),
    )

    return VcsConfig(hooks=hooks, branch=branch, signing=signing)
