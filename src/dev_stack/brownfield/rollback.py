"""Git-based rollback helpers."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from ..errors import RollbackError

ROLLBACK_PREFIX = "dev-stack/rollback"


def create_rollback_tag(repo_root: Path, *, prefix: str = ROLLBACK_PREFIX) -> str | None:
    if not _has_commits(repo_root):
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag_name = f"{prefix}/{timestamp}"
    result = _run_git(repo_root, ["tag", tag_name])
    if result.returncode != 0:
        raise RollbackError(tag_name, result.stderr.strip() or "unknown error")
    return tag_name


def restore_rollback(repo_root: Path, ref: str, paths: Sequence[Path] | None = None) -> None:
    args = ["checkout", ref, "--"]
    if paths:
        args.extend(str(path) for path in paths)
    else:
        args.append(".")
    result = _run_git(repo_root, args)
    if result.returncode != 0:
        raise RollbackError(ref, result.stderr.strip() or "git checkout failed")
    if paths is None:
        clean = _run_git(repo_root, ["clean", "-fd"])
        if clean.returncode != 0:
            raise RollbackError(ref, clean.stderr.strip() or "git clean failed")


def list_rollback_tags(repo_root: Path, *, prefix: str = ROLLBACK_PREFIX) -> list[str]:
    result = _run_git(repo_root, ["tag", "-l", f"{prefix}/*"])
    if result.returncode != 0:
        raise RollbackError(prefix, result.stderr.strip() or "unable to list tags")
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return sorted(tags)


def delete_tags(repo_root: Path, tags: Iterable[str]) -> None:
    for tag in tags:
        result = _run_git(repo_root, ["tag", "-d", tag])
        if result.returncode != 0:
            raise RollbackError(tag, result.stderr.strip() or "unable to delete tag")


def _has_commits(repo_root: Path) -> bool:
    result = _run_git(repo_root, ["rev-parse", "--verify", "HEAD"])
    return result.returncode == 0


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
