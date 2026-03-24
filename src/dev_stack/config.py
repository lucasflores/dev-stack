"""Global configuration helpers for dev-stack."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import AgentUnavailableError, ConfigError
from .manifest import AgentConfig as ManifestAgentConfig, StackManifest

AGENT_PRIORITY = ("claude", "copilot", "cursor")

_EXCLUDED_DIRS = frozenset({".git", ".venv", "venv", "node_modules", ".dev-stack", "__pycache__"})


@dataclass(frozen=True, slots=True)
class StackProfile:
    """Detected language/tooling profile for a repository."""

    has_python: bool = False


def detect_stack_profile(repo_root: Path) -> StackProfile:
    """Detect the language/tooling stack of the target repository."""
    for py_file in repo_root.rglob("*.py"):
        if not _EXCLUDED_DIRS.intersection(py_file.relative_to(repo_root).parts):
            return StackProfile(has_python=True)
    return StackProfile()


@dataclass(slots=True)
class AgentInfo:
    """Result of agent detection."""

    cli: str
    path: str | None


def _detect_from_manifest(manifest: StackManifest | None) -> AgentInfo | None:
    if manifest and manifest.agent and manifest.agent.cli != "none":
        detected_path = manifest.agent.path
        if detected_path and Path(detected_path).exists():
            return AgentInfo(cli=manifest.agent.cli, path=detected_path)
        return AgentInfo(cli=manifest.agent.cli, path=shutil.which(manifest.agent.cli))
    return None


def detect_agent(manifest: StackManifest | None = None) -> AgentInfo:
    """Detect the available coding agent CLI.

    Detection order:
        1. DEV_STACK_AGENT env var
        2. Manifest [agent] section (if provided)
        3. Local binaries in AGENT_PRIORITY order
    """

    explicit = os.getenv("DEV_STACK_AGENT")
    if explicit:
        cli = explicit.lower()
        if cli == "none":
            return AgentInfo(cli="none", path=None)
        resolved = _resolve_cli(cli)
        if resolved:
            return resolved

    manifest_candidate = _detect_from_manifest(manifest)
    if manifest_candidate:
        return manifest_candidate

    for candidate in AGENT_PRIORITY:
        resolved = _resolve_cli(candidate)
        if resolved:
            return resolved

    return AgentInfo(cli="none", path=None)


def ensure_agent_available(manifest: StackManifest | None = None) -> AgentInfo:
    """Ensure an agent is configured or raise AgentUnavailableError."""

    info = detect_agent(manifest)
    if info.cli == "none" or not info.path:
        raise AgentUnavailableError("AgentBridge")
    return info


def validate_env_vars(required_vars: Iterable[str]) -> dict[str, bool]:
    """Return a mapping of env vars to presence booleans."""

    results: dict[str, bool] = {}
    for var in required_vars:
        value = os.getenv(var)
        results[var] = bool(value)
    return results


def assert_env_vars(required_vars: Iterable[str]) -> None:
    """Raise ConfigError if any required environment variables are missing."""

    results = validate_env_vars(required_vars)
    missing = [var for var, present in results.items() if not present]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")


def _resolve_cli(candidate: str) -> AgentInfo | None:
    candidate = candidate.lower()
    if candidate == "copilot":
        gh_path = shutil.which("gh")
        if not gh_path:
            return None
        if not _gh_copilot_available(gh_path):
            return None
        return AgentInfo(cli="copilot", path=gh_path)
    path = shutil.which(candidate)
    if path:
        return AgentInfo(cli=candidate, path=path)
    return None


def _gh_copilot_available(gh_path: str) -> bool:
    try:
        subprocess.run(
            [gh_path, "copilot", "--help"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:  # pragma: no cover - defensive
        return False
