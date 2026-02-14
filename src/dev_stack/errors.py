"""Error hierarchy for dev-stack."""
from __future__ import annotations

from typing import Iterable, List, Sequence


class DevStackError(Exception):
    """Base exception for dev-stack."""


class ConflictError(DevStackError):
    """Raised when proposed module changes conflict with user content."""

    def __init__(self, conflicts: Sequence["FileConflict"]) -> None:  # pragma: no cover - simple init
        self.conflicts: List["FileConflict"] = list(conflicts)
        conflict_paths = ", ".join(str(c.path) for c in self.conflicts)
        super().__init__(f"Conflicts detected in: {conflict_paths}")


class DependencyError(DevStackError):
    """Raised when required modules are missing."""

    def __init__(self, module: str, missing: Iterable[str]) -> None:
        self.module = module
        self.missing = list(missing)
        super().__init__(f"Module '{module}' requires {', '.join(self.missing)}")


class AgentUnavailableError(DevStackError):
    """Raised when an agent CLI is required but not available."""

    def __init__(self, required_by: str) -> None:
        self.required_by = required_by
        super().__init__(f"No coding agent available for '{required_by}'")


class RollbackError(DevStackError):
    """Raised when rollback operations fail."""

    def __init__(self, ref: str, reason: str) -> None:
        self.ref = ref
        self.reason = reason
        super().__init__(f"Failed to restore rollback ref '{ref}': {reason}")


class ManifestError(DevStackError):
    """Raised when the manifest file is missing or invalid."""


class ConfigError(DevStackError):
    """Raised when configuration or environment validation fails."""


del Iterable, Sequence, List
