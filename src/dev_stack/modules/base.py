"""Module contract implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..brownfield import markers


@dataclass(slots=True)
class ModuleResult:
    success: bool
    message: str
    files_created: list[Path] = field(default_factory=list)
    files_modified: list[Path] = field(default_factory=list)
    files_deleted: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModuleStatus:
    name: str
    installed: bool
    version: str
    healthy: bool
    issue: str | None = None
    config: dict[str, Any] | None = None


class ModuleBase(ABC):
    """Base class for all dev-stack modules."""

    NAME: str
    VERSION: str
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = ()

    def __init__(
        self,
        repo_root: Path,
        manifest: dict[str, Any] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.manifest = manifest or {}

    @abstractmethod
    def install(self, *, force: bool = False) -> ModuleResult:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def uninstall(self) -> ModuleResult:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def update(self) -> ModuleResult:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def verify(self) -> ModuleStatus:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- Shared helpers -------------------------------------------------

    def read_managed_section(self, file_path: Path, section_id: str) -> str | None:
        target = self.repo_root / file_path
        return markers.read_managed_section(target, section_id)

    def write_managed_section(self, file_path: Path, section_id: str, content: str) -> bool:
        target = self.repo_root / file_path
        return markers.write_managed_section(target, section_id, content)

    # --- Brownfield preview helpers ------------------------------------

    def preview_files(self) -> dict[Path, str]:
        """Return proposed file contents for conflict detection.

        Modules can override to provide the exact text they intend to write
        so the CLI can detect brownfield overlaps before installation.
        Paths must be relative to the repository root. The base
        implementation returns an empty mapping for modules that do not
        support preview mode.
        """

        return {}
