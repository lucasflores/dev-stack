"""Shared CLI helpers for dev-stack subcommands."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Sequence

import click

from ..brownfield.conflict import ConflictReport
from ..modules.base import ModuleBase


def ensure_git_repo(repo_root: Path) -> None:
    """Initialize a git repository if one does not already exist."""

    git_dir = repo_root / ".git"
    if git_dir.exists():
        return
    run_git_command(repo_root, ["init"])


def run_git_command(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def parse_modules(modules_csv: str | None) -> list[str]:
    if not modules_csv:
        return []
    return [module.strip() for module in modules_csv.split(",") if module.strip()]


def collect_proposed_files(
    modules: Sequence[ModuleBase],
) -> tuple[dict[str, str], dict[Path, str]]:
    detection_map: dict[str, str] = {}
    lookup_map: dict[Path, str] = {}
    for module in modules:
        previews = module.preview_files()
        for rel_path, content in previews.items():
            rel = Path(rel_path)
            if rel.is_absolute():
                try:
                    rel = rel.relative_to(module.repo_root)
                except ValueError:
                    pass
            abs_path = rel if rel.is_absolute() else module.repo_root / rel
            detection_map[str(rel)] = content
            lookup_map[abs_path] = content
    return detection_map, lookup_map


def apply_post_install_overrides(
    skip_map: dict[Path, tuple[bytes, int | None]],
    merge_map: dict[Path, str],
) -> None:
    for path, (data, mode) in skip_map.items():
        path.write_bytes(data)
        if mode is not None:
            path.chmod(mode)
    for path, text in merge_map.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def has_existing_conflicts(report: ConflictReport) -> bool:
    return any(conflict.current_hash for conflict in report.conflicts)


def emit_manifest_error(ctx, message: str, *, exit_code: int) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)
    raise SystemExit(exit_code)
