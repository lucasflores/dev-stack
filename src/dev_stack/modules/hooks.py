"""Hooks module implementation."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..brownfield.conflict import ConflictType, FileConflict
from ..brownfield.markers import write_managed_section
from ..config import StackProfile, detect_stack_profile
from ..errors import ConflictError
from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "hooks"


@dataclass(frozen=True, slots=True)
class HookEntry:
    """A single pre-commit hook definition."""

    id: str
    name: str
    entry: str
    language: str = "system"
    pass_filenames: bool = False
    types: tuple[str, ...] = ()
    stages: tuple[str, ...] = ("commit",)


def _build_hook_list(profile: StackProfile) -> list[HookEntry]:
    """Build list of hooks based on the detected stack profile."""
    hooks: list[HookEntry] = [
        HookEntry(
            id="dev-stack-pipeline",
            name="dev-stack pipeline",
            entry="dev-stack pipeline run",
            stages=("commit",),
        ),
    ]
    if profile.has_python:
        hooks.extend([
            HookEntry(id="dev-stack-ruff", name="ruff lint", entry="ruff check", pass_filenames=True),
            HookEntry(id="dev-stack-pytest", name="pytest quick suite", entry="pytest -q"),
            HookEntry(
                id="dev-stack-mypy",
                name="mypy type check",
                entry="python3 -m mypy src/",
                types=("python",),
            ),
        ])
    return hooks


def _render_pre_commit_config(hooks: list[HookEntry]) -> str:
    """Render hooks as YAML string for managed section content."""
    lines: list[str] = ["repos:", "  - repo: local", "    hooks:"]
    for hook in hooks:
        lines.append(f"      - id: {hook.id}")
        lines.append(f"        name: {hook.name}")
        lines.append(f"        entry: {hook.entry}")
        lines.append(f"        language: {hook.language}")
        lines.append(f"        pass_filenames: {'true' if hook.pass_filenames else 'false'}")
        if hook.types:
            types_str = ", ".join(hook.types)
            lines.append(f"        types: [{types_str}]")
        if hook.stages:
            stages_str = ", ".join(hook.stages)
            lines.append(f"        stages: [{stages_str}]")
    return "\n".join(lines)


class HooksModule(ModuleBase):
    """Install git hooks and pre-commit configuration."""

    NAME = "hooks"
    VERSION = "0.1.0"
    MANAGED_FILES = (".pre-commit-config.yaml", "scripts/hooks/pre-commit", "scripts/hooks/prepare-commit-msg")

    def install(self, *, force: bool = False) -> ModuleResult:
        scripts_dir = self.repo_root / "scripts" / "hooks"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        script_template = TEMPLATE_DIR / "pre-commit"
        script_dest = scripts_dir / "pre-commit"

        self._copy_with_permission(script_template, script_dest, 0o755, force, created, modified)

        # Programmatic generation of .pre-commit-config.yaml via managed section
        profile = self.stack_profile or detect_stack_profile(self.repo_root)
        hooks = _build_hook_list(profile)
        rendered = _render_pre_commit_config(hooks)
        config_dest = self.repo_root / ".pre-commit-config.yaml"
        existed = config_dest.exists()
        changed = write_managed_section(config_dest, "HOOKS", rendered)
        if changed:
            (modified if existed else created).append(config_dest)

        hook_dest = self.repo_root / ".git" / "hooks" / "pre-commit"
        hook_dest.parent.mkdir(parents=True, exist_ok=True)
        self._copy_with_permission(script_template, hook_dest, 0o755, force, created, modified)

        # Install prepare-commit-msg hook (stages 3-9)
        pcm_template = TEMPLATE_DIR / "prepare-commit-msg"
        if pcm_template.exists():
            pcm_hook_dest = self.repo_root / ".git" / "hooks" / "prepare-commit-msg"
            self._copy_with_permission(pcm_template, pcm_hook_dest, 0o755, force, created, modified)
            pcm_script_dest = scripts_dir / "prepare-commit-msg"
            self._copy_with_permission(pcm_template, pcm_script_dest, 0o755, force, created, modified)

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
        profile = self.stack_profile or detect_stack_profile(self.repo_root)
        hooks = _build_hook_list(profile)
        config_content = _render_pre_commit_config(hooks)
        return {
            Path("scripts/hooks/pre-commit"): script_template,
            Path(".pre-commit-config.yaml"): config_content,
            Path(".git/hooks/pre-commit"): script_template,
        }


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(HooksModule)
