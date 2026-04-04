"""Hooks module implementation."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..brownfield.conflict import ConflictType, FileConflict
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


def _build_hook_list() -> list[HookEntry]:
    """Build list of hooks for the project."""
    return [
        HookEntry(
            id="dev-stack-pipeline",
            name="dev-stack pipeline",
            entry="dev-stack pipeline run",
            stages=("commit",),
        ),
        HookEntry(id="dev-stack-ruff", name="ruff lint", entry="ruff check", pass_filenames=True),
        HookEntry(id="dev-stack-pytest", name="pytest quick suite", entry="pytest -q"),
        HookEntry(
            id="dev-stack-mypy",
            name="mypy type check",
            entry="python3 -m mypy src/",
            types=("python",),
        ),
    ]


def _hook_entry_to_dict(hook: HookEntry) -> dict[str, Any]:
    """Convert a HookEntry to a pre-commit hook dict."""
    d: dict[str, Any] = {
        "id": hook.id,
        "name": hook.name,
        "entry": hook.entry,
        "language": hook.language,
        "pass_filenames": hook.pass_filenames,
    }
    if hook.types:
        d["types"] = list(hook.types)
    if hook.stages:
        d["stages"] = list(hook.stages)
    return d


def _render_pre_commit_config(hooks: list[HookEntry]) -> str:
    """Render hooks as YAML string for a fresh .pre-commit-config.yaml."""
    data = {
        "repos": [
            {
                "repo": "local",
                "hooks": [_hook_entry_to_dict(h) for h in hooks],
            }
        ]
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def _write_pre_commit_config(config_dest: Path, hooks: list[HookEntry]) -> bool:
    """Write dev-stack hooks to .pre-commit-config.yaml using YAML-aware merge.

    Dev-stack hook entries (ids prefixed with ``dev-stack-``) in the ``local``
    repo are replaced on each call; all other repos and hooks are preserved.
    Returns ``True`` if the file was changed.
    """
    ds_hook_dicts = [_hook_entry_to_dict(h) for h in hooks]

    if not config_dest.exists():
        content = _render_pre_commit_config(hooks)
        config_dest.write_text(content, encoding="utf-8")
        return True

    existing_text = config_dest.read_text(encoding="utf-8")
    try:
        existing: dict[str, Any] = yaml.safe_load(existing_text) or {}
    except yaml.YAMLError:
        # Unparseable YAML — overwrite with just dev-stack hooks.
        config_dest.write_text(_render_pre_commit_config(hooks), encoding="utf-8")
        return True

    repos: list[dict[str, Any]] = list(existing.get("repos") or [])

    # Locate any existing ``local`` repo entry.
    local_idx = next(
        (i for i, r in enumerate(repos) if isinstance(r, dict) and r.get("repo") == "local"),
        None,
    )

    if local_idx is None:
        # No local repo yet — prepend one with dev-stack hooks.
        repos.insert(0, {"repo": "local", "hooks": ds_hook_dicts})
    else:
        local_repo = repos[local_idx]
        existing_hooks: list[dict[str, Any]] = list(local_repo.get("hooks") or [])
        # Keep user hooks (those without the dev-stack- id prefix).
        user_hooks = [
            h for h in existing_hooks
            if isinstance(h, dict) and not str(h.get("id", "")).startswith("dev-stack-")
        ]
        repos[local_idx] = {**local_repo, "hooks": ds_hook_dicts + user_hooks}

    existing["repos"] = repos
    new_text = yaml.dump(existing, default_flow_style=False, sort_keys=False)

    if new_text == existing_text:
        return False

    config_dest.write_text(new_text, encoding="utf-8")
    return True


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

        # .pre-commit-config.yaml: YAML-aware merge keeps user hooks intact.
        hooks = _build_hook_list()
        config_dest = self.repo_root / ".pre-commit-config.yaml"
        existed = config_dest.exists()
        changed = _write_pre_commit_config(config_dest, hooks)
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
        hooks = _build_hook_list()
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
