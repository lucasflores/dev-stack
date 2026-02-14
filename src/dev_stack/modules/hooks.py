"""Hooks module implementation."""
from __future__ import annotations

import shutil
from pathlib import Path

from ..brownfield.conflict import ConflictType, FileConflict
from ..errors import ConflictError
from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "hooks"


class HooksModule(ModuleBase):
    """Install git hooks and pre-commit configuration."""

    NAME = "hooks"
    VERSION = "0.1.0"
    MANAGED_FILES = (".pre-commit-config.yaml", "scripts/hooks/pre-commit")

    def install(self, *, force: bool = False) -> ModuleResult:
        scripts_dir = self.repo_root / "scripts" / "hooks"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        script_template = TEMPLATE_DIR / "pre-commit"
        script_dest = scripts_dir / "pre-commit"
        config_template = TEMPLATE_DIR / "pre-commit-config.yaml"
        config_dest = self.repo_root / ".pre-commit-config.yaml"

        self._copy_with_permission(script_template, script_dest, 0o755, force, created, modified)
        self._copy_with_permission(config_template, config_dest, 0o644, force, created, modified)

        hook_dest = self.repo_root / ".git" / "hooks" / "pre-commit"
        hook_dest.parent.mkdir(parents=True, exist_ok=True)
        self._copy_with_permission(script_template, hook_dest, 0o755, force, created, modified)

        return ModuleResult(
            success=True,
            message="Hooks installed",
            files_created=created,
            files_modified=modified,
            warnings=warnings,
        )

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        for rel_path in self.MANAGED_FILES:
            path = self.repo_root / rel_path
            if path.exists():
                path.unlink()
                deleted.append(path)
        hook = self.repo_root / ".git" / "hooks" / "pre-commit"
        if hook.exists():
            hook.unlink()
            deleted.append(hook)
        return ModuleResult(True, "Hooks removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        all_files = [self.repo_root / path for path in self.MANAGED_FILES]
        all_files.append(self.repo_root / ".git" / "hooks" / "pre-commit")
        healthy = all(path.exists() for path in all_files)
        issue = None if healthy else "One or more hook files missing"
        return ModuleStatus(
            name=self.NAME,
            installed=True,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
        )

    # ------------------------------------------------------------------
    def _copy_with_permission(
        self,
        template_path: Path,
        destination: Path,
        mode: int,
        force: bool,
        created: list[Path],
        modified: list[Path],
    ) -> None:
        existed = destination.exists()
        if existed and not force:
            raise ConflictError(
                [
                    FileConflict(
                        path=destination,
                        conflict_type=ConflictType.MODIFIED,
                        proposed_hash="",
                        current_hash="",
                    )
                ]
            )
        shutil.copy2(template_path, destination)
        destination.chmod(mode)
        if existed:
            modified.append(destination)
        else:
            created.append(destination)

    def preview_files(self) -> dict[Path, str]:
        script_template = (TEMPLATE_DIR / "pre-commit").read_text(encoding="utf-8")
        config_template = (TEMPLATE_DIR / "pre-commit-config.yaml").read_text(encoding="utf-8")
        return {
            Path("scripts/hooks/pre-commit"): script_template,
            Path(".pre-commit-config.yaml"): config_template,
            Path(".git/hooks/pre-commit"): script_template,
        }


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(HooksModule)
