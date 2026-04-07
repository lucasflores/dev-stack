"""Conflict detection utilities."""
from __future__ import annotations

import hashlib
import difflib
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping

import click


class ConflictType(str, Enum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"


def is_greenfield_uv_package(pyproject_path: Path) -> bool:
    """Return True if pyproject.toml matches untouched ``uv init --package`` output."""
    import tomllib

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return False

    build_system = data.get("build-system", {})
    if build_system.get("build-backend") != "uv_build":
        return False

    project = data.get("project", {})
    if project.get("description") != "Add your description here":
        return False

    if "tool" in data:
        return False

    # FR-002: Check for pre-existing Python sources at repo root (depth 1).
    from ..modules.uv_project import scan_root_python_sources

    repo_root = pyproject_path.parent
    has_python, _packages = scan_root_python_sources(repo_root)
    if has_python:
        return False

    return True


@dataclass(slots=True)
class FileConflict:
    path: Path
    conflict_type: ConflictType
    proposed_hash: str
    current_hash: str | None = None
    diff: str | None = None
    resolution: str = "pending"


@dataclass(slots=True)
class ConflictReport:
    operation: str
    conflicts: list[FileConflict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def all_resolved(self) -> bool:
        return all(conflict.resolution != "pending" for conflict in self.conflicts)


def detect_conflicts(
    repo_root: Path,
    proposed_files: Mapping[str | Path, str | None],
) -> list[FileConflict]:
    """Detect conflicts between existing files and proposed contents."""

    conflicts: list[FileConflict] = []
    for rel_path, proposed_text in proposed_files.items():
        abs_path = repo_root / Path(rel_path)
        if proposed_text is None:
            if abs_path.exists():
                current_hash = _hash_bytes(abs_path.read_bytes())
                conflicts.append(
                    FileConflict(
                        path=abs_path,
                        conflict_type=ConflictType.DELETED,
                        proposed_hash="0" * 64,
                        current_hash=current_hash,
                    )
                )
            continue

        proposed_hash = _hash_bytes(proposed_text.encode("utf-8"))
        if not abs_path.exists():
            conflicts.append(
                FileConflict(
                    path=abs_path,
                    conflict_type=ConflictType.NEW,
                    proposed_hash=proposed_hash,
                    current_hash=None,
                )
            )
            continue

        current_text = abs_path.read_text(encoding="utf-8")
        current_hash = _hash_bytes(current_text.encode("utf-8"))
        if current_hash == proposed_hash:
            continue

        diff = "".join(
            difflib.unified_diff(
                current_text.splitlines(keepends=True),
                proposed_text.splitlines(keepends=True),
                fromfile=str(abs_path),
                tofile=f"proposed::{abs_path}",
            )
        )
        conflicts.append(
            FileConflict(
                path=abs_path,
                conflict_type=ConflictType.MODIFIED,
                proposed_hash=proposed_hash,
                current_hash=current_hash,
                diff=diff or None,
            )
        )
    return conflicts


def build_conflict_report(
    operation: str,
    repo_root: Path,
    proposed_files: Mapping[str | Path, str | None],
) -> ConflictReport:
    return ConflictReport(operation=operation, conflicts=detect_conflicts(repo_root, proposed_files))


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialize_conflicts(report: ConflictReport, repo_root: Path) -> list[dict[str, str | None]]:
    """Return a JSON-friendly conflict representation."""

    payload: list[dict[str, str | None]] = []
    for conflict in report.conflicts:
        try:
            rel_path = conflict.path.relative_to(repo_root)
        except ValueError:
            rel_path = conflict.path
        payload.append(
            {
                "path": str(rel_path),
                "type": conflict.conflict_type.value,
                "resolution": conflict.resolution,
            }
        )
    return payload


def echo_conflict_summary(report: ConflictReport, repo_root: Path) -> None:
    """Print a concise summary of conflicts for human output."""

    if not report.conflicts:
        click.secho("No conflicting files detected.", fg="green")
        return
    click.secho("Potential conflicts detected:", fg="yellow")
    for conflict in report.conflicts:
        try:
            rel_path = conflict.path.relative_to(repo_root)
        except ValueError:
            rel_path = conflict.path
        status = conflict.conflict_type.value.upper()
        click.echo(f" - {rel_path} [{status}]")


def resolve_conflicts_interactively(
    report: ConflictReport,
    repo_root: Path,
    proposed_files: Mapping[Path, str],
) -> tuple[dict[Path, tuple[bytes, int | None]], dict[Path, str]]:
    """Prompt the user to resolve conflicts one-by-one."""

    blocking = [conflict for conflict in report.conflicts if conflict.current_hash]
    skip_map: dict[Path, tuple[bytes, int | None]] = {}
    merge_map: dict[Path, str] = {}
    if not blocking:
        return skip_map, merge_map

    click.secho("Interactive conflict resolution", fg="yellow")
    click.echo("Options: [a]ccept overwrite  [s]kip  [m]erge in editor  [q]uit")
    for conflict in blocking:
        try:
            rel_path = conflict.path.relative_to(repo_root)
        except ValueError:
            rel_path = conflict.path
        click.secho(f"\nCONFLICT: {rel_path}", fg="bright_yellow")
        if conflict.diff:
            click.echo(conflict.diff)
        choice = _prompt_choice()
        if choice == "q":
            raise click.Abort()
        if choice == "a":
            conflict.resolution = "accepted"
            continue
        if choice == "s":
            conflict.resolution = "skipped"
            skip_map[conflict.path] = _snapshot_file(conflict.path)
            continue
        if choice == "m":
            proposed_text = proposed_files.get(conflict.path) or proposed_files.get(rel_path)
            merged = _launch_merge_editor(conflict, repo_root, proposed_text)
            if merged is None:
                conflict.resolution = "skipped"
                skip_map[conflict.path] = _snapshot_file(conflict.path)
            else:
                conflict.resolution = "merged"
                merge_map[conflict.path] = merged
    return skip_map, merge_map


def _prompt_choice() -> str:
    return click.prompt("Choose", type=click.Choice(["a", "s", "m", "q"], case_sensitive=False)).lower()


def _snapshot_file(path: Path) -> tuple[bytes, int | None]:
    if not path.exists():
        return b"", None
    data = path.read_bytes()
    mode = path.stat().st_mode
    return data, mode


def _launch_merge_editor(
    conflict: FileConflict,
    repo_root: Path,
    proposed_text: str | None,
) -> str | None:
    current_text = conflict.path.read_text(encoding="utf-8") if conflict.path.exists() else ""
    prompt_path = conflict.path
    try:
        prompt_path = conflict.path.relative_to(repo_root)
    except ValueError:
        pass
    header = textwrap.dedent(
        f"""# Merge dev-stack changes for {prompt_path}
# Lines beginning with '# ' will be removed.
<<<<<<< CURRENT
"""
    )
    initial = "".join([header, current_text, "\n======= PROPOSED\n", proposed_text or "", "\n>>>>>>> END\n"])
    edited = click.edit(initial, extension=".tmp")
    if edited is None:
        return None
    filtered_lines = [line for line in edited.splitlines() if not line.startswith("# ")]
    return "\n".join(filtered_lines)
