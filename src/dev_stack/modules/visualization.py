"""Visualization module."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import detect_agent
from ..errors import AgentUnavailableError, DependencyError
from .base import ModuleBase, ModuleResult, ModuleStatus

DOCS_DIR = Path("docs/diagrams")
VIZ_STATE_DIR = Path(".dev-stack/viz")
D2_MIN_VERSION = "0.6"


def _ensure_d2_installed() -> tuple[bool, str | None]:
    path = shutil.which("d2")
    if path:
        return True, path
    if shutil.which("brew"):
        process = subprocess.run(
            ["brew", "install", "d2"],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            new_path = shutil.which("d2")
            if new_path:
                return True, new_path
        return False, process.stderr or process.stdout
    return False, "D2 CLI not found; install from https://d2lang.com/tour/install/"


def _d2_version(path: str) -> str | None:
    process = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return None
    first_line = process.stdout.strip().splitlines()[0]
    return first_line.split()[-1]


class VisualizationModule(ModuleBase):
    NAME = "visualization"
    VERSION = "0.1.0"
    MANAGED_FILES = (str(DOCS_DIR), str(VIZ_STATE_DIR))

    def install(self, *, force: bool = False) -> ModuleResult:
        docs_dir = self.repo_root / DOCS_DIR
        docs_dir.mkdir(parents=True, exist_ok=True)
        viz_dir = self.repo_root / VIZ_STATE_DIR
        viz_dir.mkdir(parents=True, exist_ok=True)
        success, error = _ensure_d2_installed()
        warnings: list[str] = []
        if not success:
            warnings.append(error or "Failed to install D2 CLI")
        else:
            version = _d2_version(shutil.which("d2"))
            if not version or version < D2_MIN_VERSION:
                warnings.append("D2 CLI version is outdated; please upgrade to >=0.6")
        return ModuleResult(True, "Visualization directories prepared", [docs_dir, viz_dir], warnings=warnings)

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        docs_dir = self.repo_root / DOCS_DIR
        if docs_dir.exists():
            shutil.rmtree(docs_dir)
            deleted.append(docs_dir)
        viz_dir = self.repo_root / VIZ_STATE_DIR
        if viz_dir.exists():
            shutil.rmtree(viz_dir)
            deleted.append(viz_dir)
        return ModuleResult(True, "Visualization assets removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        docs_dir = self.repo_root / DOCS_DIR
        viz_dir = self.repo_root / VIZ_STATE_DIR
        installed = docs_dir.exists() and viz_dir.exists()
        d2_path = shutil.which("d2")
        version = _d2_version(d2_path) if d2_path else None
        healthy = installed and d2_path is not None and version is not None
        issue = None
        if not installed:
            issue = "Visualization directories missing"
        elif not d2_path:
            issue = "D2 CLI not found"
        elif version is None:
            issue = "Unable to determine D2 version"
        return ModuleStatus(
            name=self.NAME,
            installed=installed,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
            config={"d2_path": d2_path, "d2_version": version},
        )
