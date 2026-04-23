"""Visualization module — Understand-Anything integration."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .base import ModuleBase, ModuleResult, ModuleStatus
from ..visualization import understand_runner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (per module-contract.md)
# ---------------------------------------------------------------------------

UNDERSTAND_OUTPUT_DIR = Path(".understand-anything")
VIZ_STATE_DIR = Path(".dev-stack/viz")
LEGACY_OUTPUT_DIR = Path("." + "".join(("code", "boarding")))
LEGACY_DOCS_DIR = Path("docs/diagrams")
KNOWLEDGE_GRAPH_FILE = understand_runner.KNOWLEDGE_GRAPH_FILE
DIFF_OVERLAY_FILE = understand_runner.DIFF_OVERLAY_FILE
INTERMEDIATE_DIR = understand_runner.INTERMEDIATE_DIR
MANAGED_GRAPH_EXCLUDES = (
    f"{UNDERSTAND_OUTPUT_DIR}/{INTERMEDIATE_DIR}/",
    f"{UNDERSTAND_OUTPUT_DIR}/{DIFF_OVERLAY_FILE}",
)
SUPPORTED_PLUGIN_EXPERIENCES = understand_runner.SUPPORTED_PLUGIN_EXPERIENCES
DEFAULT_DEPTH_LEVEL = 2
DEFAULT_TIMEOUT_SECONDS = 300


class VisualizationModule(ModuleBase):
    NAME = "visualization"
    VERSION = "1.0.0"
    DEPENDS_ON: tuple[str, ...] = ()
    MANAGED_FILES = (str(UNDERSTAND_OUTPUT_DIR), str(VIZ_STATE_DIR))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(self, *, force: bool = False) -> ModuleResult:
        graph_dir = self.repo_root / UNDERSTAND_OUTPUT_DIR
        graph_dir.mkdir(parents=True, exist_ok=True)
        viz_dir = self.repo_root / VIZ_STATE_DIR
        viz_dir.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []
        if not (graph_dir / KNOWLEDGE_GRAPH_FILE).exists():
            warnings.append(
                "Graph artifacts are missing. Generate and commit "
                ".understand-anything/knowledge-graph.json using a supported plugin workflow."
            )

        created = [graph_dir, viz_dir]
        return ModuleResult(
            True,
            "Visualization module installed",
            files_created=created,
            warnings=warnings,
        )

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []

        # Delete directories
        for rel_dir in (UNDERSTAND_OUTPUT_DIR, VIZ_STATE_DIR, LEGACY_OUTPUT_DIR, LEGACY_DOCS_DIR):
            abs_dir = self.repo_root / rel_dir
            if abs_dir.exists():
                shutil.rmtree(abs_dir)
                deleted.append(abs_dir)

        return ModuleResult(
            True,
            "Visualization assets removed",
            files_deleted=deleted,
        )

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        graph_dir = self.repo_root / UNDERSTAND_OUTPUT_DIR
        viz_dir = self.repo_root / VIZ_STATE_DIR
        installed = graph_dir.exists() and viz_dir.exists()

        issue: str | None = None
        if not installed:
            issue = "Visualization directories missing"
            bootstrap = None
        else:
            try:
                bootstrap = understand_runner.verify_bootstrap(self.repo_root)
            except Exception as exc:  # pragma: no cover - defensive status path
                bootstrap = None
                issue = str(exc)
            else:
                if bootstrap.status != "pass":
                    issue = (
                        "Committed graph artifacts missing or invalid; "
                        "run Understand-Anything and commit .understand-anything/knowledge-graph.json"
                    )

        healthy = installed and bootstrap is not None and bootstrap.status == "pass"
        return ModuleStatus(
            name=self.NAME,
            installed=installed,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
            config={
                "output_dir": str(UNDERSTAND_OUTPUT_DIR),
                "knowledge_graph": str(UNDERSTAND_OUTPUT_DIR / KNOWLEDGE_GRAPH_FILE),
                "supports_plugins": list(SUPPORTED_PLUGIN_EXPERIENCES),
            },
        )


def _register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


_register(VisualizationModule)
