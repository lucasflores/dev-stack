# Module Contract: dev-stack Modules

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

---

## Module Abstract Base Class

All modules extend `ModuleBase` in `src/dev_stack/modules/base.py`.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ModuleResult:
    """Standard result from any module operation."""
    success: bool
    message: str
    files_created: list[Path]
    files_modified: list[Path]
    files_deleted: list[Path]
    warnings: list[str]


@dataclass
class ModuleStatus:
    """Health/status report for a module."""
    name: str
    installed: bool
    version: str
    healthy: bool
    issue: str | None = None
    config: dict[str, Any] | None = None


class ModuleBase(ABC):
    """Base class for all dev-stack modules."""

    # --- Class attributes (override in subclasses) ---
    NAME: str                          # Unique module identifier
    VERSION: str                       # Module semver
    DEPENDS_ON: list[str] = []         # Names of required modules
    MANAGED_FILES: list[str] = []      # Relative paths this module owns

    def __init__(self, repo_root: Path, manifest: dict) -> None:
        self.repo_root = repo_root
        self.manifest = manifest

    @abstractmethod
    def install(self, *, force: bool = False) -> ModuleResult:
        """Add this module to the repository.

        Args:
            force: If True, overwrite existing files without conflict check.

        Returns:
            ModuleResult with created/modified files.

        Raises:
            ConflictError: If force=False and managed files already exist
                           with content outside marker-delimited sections.
        """
        ...

    @abstractmethod
    def uninstall(self) -> ModuleResult:
        """Remove this module's files and configuration.

        Only removes content within marker-delimited sections.
        Never deletes files that contain user content outside markers.

        Returns:
            ModuleResult with deleted/modified files.
        """
        ...

    @abstractmethod
    def update(self) -> ModuleResult:
        """Update this module to the latest version.

        Must preserve user content outside marker-delimited sections.

        Returns:
            ModuleResult with modified files.
        """
        ...

    @abstractmethod
    def verify(self) -> ModuleStatus:
        """Check that this module is correctly installed and healthy.

        Verifies:
        - All MANAGED_FILES exist (or markers are present in shared files)
        - External tools are available (e.g., d2 CLI for visualization)
        - Configuration is valid

        Returns:
            ModuleStatus with health information.
        """
        ...

    # --- Concrete helpers (shared by all modules) ---

    def read_managed_section(self, file_path: Path, section_id: str) -> str | None:
        """Read content between markers for this module's section.

        Markers follow the format:
            # === DEV-STACK:BEGIN:<section_id> ===
            ... content ...
            # === DEV-STACK:END:<section_id> ===

        Returns:
            Content between markers, or None if markers not found.
        """
        ...

    def write_managed_section(
        self, file_path: Path, section_id: str, content: str
    ) -> bool:
        """Write content between markers, creating markers if needed.

        If markers exist: replace content between them.
        If markers don't exist: append markers + content to file.
        If file doesn't exist: create file with markers + content.

        Returns:
            True if file was modified.
        """
        ...
```

---

## Module Resolution Order

When installing multiple modules, dependency order is resolved:

```
1. hooks          (no deps)
2. speckit        (no deps)
3. ci-workflows   (no deps)
4. docker         (no deps)
5. mcp-servers    (no deps)
6. visualization  (depends on: hooks — diagrams update in pipeline stage 5)
```

If a dependency is not selected but required, it is auto-included with a warning.

---

## Module File Ownership

Each module declares the files it manages. Ownership determines:
- Which files are created during `install()`
- Which sections are updated during `update()`
- Which content is removed during `uninstall()`

| Module | Managed Files |
|--------|---------------|
| hooks | `.pre-commit-config.yaml`, `scripts/hooks/*` |
| speckit | `.specify/` (initial scaffold only) |
| ci-workflows | `.github/workflows/dev-stack-*.yml` |
| docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore` |
| mcp-servers | `.claude/settings.local.json` (Claude), `.github/copilot-mcp.json` (Copilot) |
| visualization | `docs/diagrams/*`, `.dev-stack/viz/manifest.json` |

---

## Marker Format Specification

Marker-delimited sections protect user content in shared files.

```
# === DEV-STACK:BEGIN:<module>/<section> ===
# Auto-generated by dev-stack. Do not edit between markers.
<generated content>
# === DEV-STACK:END:<module>/<section> ===
```

**Rules**:
- Comment prefix adapts to file type (`#` for YAML/Python, `//` for JS/TS, `<!-- -->` for HTML/MD)
- Multiple marker sections allowed per file
- Content outside markers is never touched by `update()` or `uninstall()`
- `install()` with `force=True` replaces entire file; without `force`, only writes within markers

---

## Error Types

```python
class DevStackError(Exception):
    """Base exception for dev-stack."""

class ConflictError(DevStackError):
    """Raised when a module file conflicts with existing content."""
    def __init__(self, conflicts: list[FileConflict]):
        self.conflicts = conflicts

class DependencyError(DevStackError):
    """Raised when a module's dependencies are not met."""
    def __init__(self, module: str, missing: list[str]):
        self.module = module
        self.missing = missing

class AgentUnavailableError(DevStackError):
    """Raised when agent is required but not configured/found."""
    def __init__(self, required_by: str):
        self.required_by = required_by

class RollbackError(DevStackError):
    """Raised when rollback fails."""
    def __init__(self, ref: str, reason: str):
        self.ref = ref
        self.reason = reason
```
