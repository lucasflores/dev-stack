"""Changelog generation — wraps git-cliff subprocess.

Provides :func:`generate_changelog` which invokes ``git-cliff`` and
post-processes output for AI/human-edited annotations.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ChangelogResult:
    """Outcome of a changelog generation run."""

    success: bool
    content: str = ""
    output_file: str = "CHANGELOG.md"
    mode: str = "unreleased"
    versions_rendered: int = 0
    total_commits_processed: int = 0
    ai_commits_annotated: int = 0
    human_edited_annotated: int = 0
    git_cliff_version: str = ""
    error: str | None = None
    help: str | None = None


def generate_changelog(
    *,
    repo_root: Path,
    unreleased: bool = True,
    full: bool = False,
    output_file: str = "CHANGELOG.md",
) -> ChangelogResult:
    """Generate a changelog using ``git-cliff``.

    Args:
        repo_root: Repository root directory.
        unreleased: Only changes since last tag (default).
        full: Complete history from all tags.
        output_file: Output file path (relative to *repo_root*).

    Returns:
        :class:`ChangelogResult` with generated content and metadata.
    """
    # 1. Check git-cliff availability
    cliff_path = shutil.which("git-cliff")
    if not cliff_path:
        return ChangelogResult(
            success=False,
            error="git-cliff is not installed",
            help="Install git-cliff: cargo install git-cliff, or brew install git-cliff",
        )

    # 2. Get git-cliff version
    try:
        ver_result = subprocess.run(
            ["git-cliff", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = ver_result.stdout.strip().replace("git-cliff ", "")
    except Exception:
        version = "unknown"

    # 3. Check cliff.toml exists
    cliff_toml = repo_root / "cliff.toml"
    if not cliff_toml.exists():
        return ChangelogResult(
            success=False,
            error="cliff.toml not found at repository root",
            help="Run 'dev-stack init' to generate cliff.toml",
            git_cliff_version=version,
        )

    # 4. Build command
    cmd = ["git-cliff"]
    mode = "full"
    if unreleased and not full:
        cmd.append("--unreleased")
        mode = "unreleased"

    cmd.extend(["--config", str(cliff_toml)])

    # 5. Run git-cliff
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        return ChangelogResult(
            success=False,
            error="git-cliff timed out after 60 seconds",
            git_cliff_version=version,
        )

    if result.returncode != 0:
        return ChangelogResult(
            success=False,
            error=f"git-cliff failed: {result.stderr.strip()}",
            git_cliff_version=version,
        )

    content = result.stdout

    # 6. Post-process: count annotations
    ai_count = content.count("🤖")
    edited_count = content.count("✏️")

    # Count versions rendered (## [x.y.z] or ## [Unreleased] headers)
    import re
    version_headers = re.findall(r"^## \[", content, re.MULTILINE)
    versions_rendered = len(version_headers)

    # Count commit lines (lines starting with "- ")
    commit_lines = [ln for ln in content.splitlines() if ln.strip().startswith("- ")]
    total_commits = len(commit_lines)

    # 7. Write to output file
    out_path = repo_root / output_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return ChangelogResult(
        success=True,
        content=content,
        output_file=output_file,
        mode=mode,
        versions_rendered=versions_rendered,
        total_commits_processed=total_commits,
        ai_commits_annotated=ai_count,
        human_edited_annotated=edited_count,
        git_cliff_version=version,
    )
