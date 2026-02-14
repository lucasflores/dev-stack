"""Spec Kit module implementation."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "speckit"
SPECIFY_DIR_NAME = ".specify"
SPEC_KIT_VERSION = "0.1.0"
SHIM_RELATIVE_PATH = Path(".dev-stack") / "bin" / "specify"
PRESERVE_FILES = {Path("memory") / "constitution.md"}


@dataclass(slots=True)
class _SyncResult:
    created: list[Path]
    modified: list[Path]


class SpecKitModule(ModuleBase):
    NAME = "speckit"
    VERSION = SPEC_KIT_VERSION
    MANAGED_FILES = (str(Path(SPECIFY_DIR_NAME)), str(SHIM_RELATIVE_PATH))

    def install(self, *, force: bool = False) -> ModuleResult:
        target_dir = self.repo_root / SPECIFY_DIR_NAME
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        sync_result = self._sync_specify_tree(target_dir, overwrite=force, preserve_existing=not force)
        created.extend(sync_result.created)
        modified.extend(sync_result.modified)

        shim_created, shim_modified = self._ensure_cli_shim()
        created.extend(shim_created)
        modified.extend(shim_modified)

        warning = self._maybe_install_cli_with_uv()
        if warning:
            warnings.append(warning)

        return ModuleResult(True, "Spec Kit scaffold installed", created, modified, warnings=warnings)

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        specify_dir = self.repo_root / SPECIFY_DIR_NAME
        if specify_dir.exists():
            shutil.rmtree(specify_dir)
            deleted.append(specify_dir)
        shim_path = self.repo_root / SHIM_RELATIVE_PATH
        if shim_path.exists():
            shim_path.unlink()
            deleted.append(shim_path)
        return ModuleResult(True, "Spec Kit scaffold removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        target_dir = self.repo_root / SPECIFY_DIR_NAME
        warnings: list[str] = []
        sync_result = self._sync_specify_tree(target_dir, overwrite=True, preserve_existing=True)
        shim_created, shim_modified = self._ensure_cli_shim()
        warning = self._maybe_install_cli_with_uv()
        if warning:
            warnings.append(warning)
        created = sync_result.created + shim_created
        modified = sync_result.modified + shim_modified
        return ModuleResult(True, "Spec Kit scaffold updated", created, modified, warnings=warnings)

    def verify(self) -> ModuleStatus:
        specify_dir = self.repo_root / SPECIFY_DIR_NAME
        constitution = specify_dir / "memory/constitution.md"
        scripts_dir = specify_dir / "scripts" / "bash"
        shim_path = self.repo_root / SHIM_RELATIVE_PATH

        healthy = specify_dir.exists() and constitution.exists() and scripts_dir.exists()
        issue = None
        if not specify_dir.exists():
            issue = ".specify/ directory missing"
        elif not constitution.exists():
            issue = "constitution not found"
        elif not scripts_dir.exists():
            issue = "Spec Kit scripts missing"
        elif not shim_path.exists():
            issue = "specify shim missing"

        return ModuleStatus(
            name=self.NAME,
            installed=specify_dir.exists(),
            version=self.VERSION,
            healthy=healthy and shim_path.exists(),
            issue=issue,
        )

    def preview_files(self) -> dict[Path, str]:
        preview: dict[Path, str] = {}
        if TEMPLATE_DIR.exists():
            for path in TEMPLATE_DIR.rglob("*"):
                if path.is_dir():
                    continue
                rel = path.relative_to(TEMPLATE_DIR)
                target = Path(SPECIFY_DIR_NAME) / rel
                preview[target] = path.read_text(encoding="utf-8")
        preview[SHIM_RELATIVE_PATH] = self._cli_shim_contents()
        return preview

    # ------------------------------------------------------------------
    def _sync_specify_tree(self, target_dir: Path, *, overwrite: bool, preserve_existing: bool) -> _SyncResult:
        created: list[Path] = []
        modified: list[Path] = []
        if not TEMPLATE_DIR.exists():
            return _SyncResult(created, modified)
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_path in TEMPLATE_DIR.rglob("*"):
            if source_path.is_dir():
                (target_dir / source_path.relative_to(TEMPLATE_DIR)).mkdir(parents=True, exist_ok=True)
                continue
            rel_path = source_path.relative_to(TEMPLATE_DIR)
            destination = target_dir / rel_path
            if preserve_existing and rel_path in PRESERVE_FILES and destination.exists():
                continue
            if destination.exists():
                if not overwrite:
                    continue
                shutil.copy2(source_path, destination)
                modified.append(destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                created.append(destination)
        return _SyncResult(created, modified)

    def _ensure_cli_shim(self) -> tuple[list[Path], list[Path]]:
        created: list[Path] = []
        modified: list[Path] = []
        shim_path = self.repo_root / SHIM_RELATIVE_PATH
        shim_path.parent.mkdir(parents=True, exist_ok=True)
        contents = self._cli_shim_contents()
        if shim_path.exists():
            current = shim_path.read_text(encoding="utf-8")
            if current == contents:
                return created, modified
            modified.append(shim_path)
        else:
            created.append(shim_path)
        shim_path.write_text(contents, encoding="utf-8")
        shim_path.chmod(0o755)
        return created, modified

    def _cli_shim_contents(self) -> str:
        return """#!/usr/bin/env bash
set -e
if command -v uv >/dev/null 2>&1; then
    exec uv tool run spec-kit -- "$@"
fi
cat <<'EOF' 1>&2
Spec Kit CLI requires the uv tool. Install uv from https://docs.astral.sh/uv/ \
then run `uv tool install spec-kit`.
EOF
exit 1
"""

    def _maybe_install_cli_with_uv(self) -> str | None:
        uv_path = shutil.which("uv")
        if not uv_path:
            return "uv CLI not found; install uv to enable Spec Kit commands"
        process = subprocess.run(
            [uv_path, "tool", "install", "spec-kit"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            cwd=self.repo_root,
            check=False,
        )
        if process.returncode != 0:
            details = process.stderr.strip() or process.stdout.strip() or "unknown error"
            return f"Failed to install Spec Kit CLI via uv: {details}"
        return None


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(SpecKitModule)
