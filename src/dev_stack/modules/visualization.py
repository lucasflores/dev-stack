"""Visualization module — CodeBoarding integration."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from .base import ModuleBase, ModuleResult, ModuleStatus
from ..visualization import codeboarding_runner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (per module-contract.md)
# ---------------------------------------------------------------------------

CODEBOARDING_OUTPUT_DIR = Path(".codeboarding")
VIZ_STATE_DIR = Path(".dev-stack/viz")
LEGACY_DOCS_DIR = Path("docs/diagrams")
ANALYSIS_INDEX = "analysis.json"
INJECTION_LEDGER = "injected-readmes.json"
ROOT_MARKER_ID = "architecture"
COMPONENT_MARKER_ID = "component-architecture"
DEFAULT_DEPTH_LEVEL = 2
DEFAULT_TIMEOUT_SECONDS = 300


class VisualizationModule(ModuleBase):
    NAME = "visualization"
    VERSION = "1.0.0"
    DEPENDS_ON: tuple[str, ...] = ()
    MANAGED_FILES = (str(CODEBOARDING_OUTPUT_DIR), str(VIZ_STATE_DIR))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(self, *, force: bool = False) -> ModuleResult:
        cb_dir = self.repo_root / CODEBOARDING_OUTPUT_DIR
        cb_dir.mkdir(parents=True, exist_ok=True)
        viz_dir = self.repo_root / VIZ_STATE_DIR
        viz_dir.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []
        if not codeboarding_runner.check_cli_available():
            warnings.append(
                "CodeBoarding CLI not found on PATH; install via 'pip install codeboarding'"
            )

        created = [cb_dir, viz_dir]
        return ModuleResult(
            True,
            "Visualization module installed",
            files_created=created,
            warnings=warnings,
        )

    def uninstall(self) -> ModuleResult:
        modified: list[Path] = []
        deleted: list[Path] = []

        # Remove managed README sections via ledger
        ledger_path = self.repo_root / CODEBOARDING_OUTPUT_DIR / INJECTION_LEDGER
        if ledger_path.exists():
            try:
                from ..visualization.readme_injector import remove_diagram

                data = json.loads(ledger_path.read_text(encoding="utf-8"))
                for entry in data.get("entries", []):
                    readme_rel = entry.get("readme_path", "")
                    marker_id = entry.get("marker_id", "")
                    if readme_rel and marker_id:
                        readme_abs = self.repo_root / readme_rel
                        try:
                            remove_diagram(readme_abs, marker_id)
                            modified.append(readme_abs)
                        except Exception:  # pragma: no cover
                            logger.warning("Failed to remove section from %s", readme_rel)
            except Exception:  # pragma: no cover
                logger.warning("Failed to read injection ledger")

        # Delete directories
        for rel_dir in (CODEBOARDING_OUTPUT_DIR, VIZ_STATE_DIR, LEGACY_DOCS_DIR):
            abs_dir = self.repo_root / rel_dir
            if abs_dir.exists():
                shutil.rmtree(abs_dir)
                deleted.append(abs_dir)

        return ModuleResult(
            True,
            "Visualization assets removed",
            files_modified=modified,
            files_deleted=deleted,
        )

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        cb_dir = self.repo_root / CODEBOARDING_OUTPUT_DIR
        viz_dir = self.repo_root / VIZ_STATE_DIR
        installed = cb_dir.exists() and viz_dir.exists()
        cli_available = codeboarding_runner.check_cli_available()
        healthy = installed and cli_available

        issue: str | None = None
        if not installed:
            issue = "Visualization directories missing"
        elif not cli_available:
            issue = "CodeBoarding CLI not found"

        cb_path = shutil.which("codeboarding")
        return ModuleStatus(
            name=self.NAME,
            installed=installed,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
            config={
                "codeboarding_path": cb_path,
                "output_dir": str(CODEBOARDING_OUTPUT_DIR),
            },
        )


def _register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


_register(VisualizationModule)
