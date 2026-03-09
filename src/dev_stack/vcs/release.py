"""Semantic release versioning — infer, bump, tag.

Provides :class:`ReleaseContext` and :func:`prepare_release`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from dev_stack.vcs.commit_parser import CommitSummary, parse_commits

# Hard-failure pipeline stages (FR-036)
_HARD_STAGES = {"lint", "typecheck", "test", "security", "docs-api"}


@dataclass(slots=True)
class HardFailure:
    """A commit with hard pipeline failures."""

    sha: str
    subject: str
    failed_stages: list[str]


@dataclass(slots=True)
class ReleaseContext:
    """Context for a semantic release operation."""

    current_version: str
    next_version: str
    bump_type: Literal["major", "minor", "patch"]
    commits: list[CommitSummary] = field(default_factory=list)
    has_breaking: bool = False
    hard_failures: list[HardFailure] = field(default_factory=list)
    tag_name: str = ""


def _read_current_version(repo_root: Path) -> str:
    """Read version from ``pyproject.toml``."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return "0.0.0"
    with open(pyproject, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("project", {}).get("version", "0.0.0")


def _bump_version(
    version: str, bump: Literal["major", "minor", "patch"]
) -> str:
    """Compute next version from *version* and *bump* type."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        return "0.1.0"
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if bump == "major":
        return f"{major + 1}.0.0"
    elif bump == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def _infer_bump(commits: list[CommitSummary]) -> Literal["major", "minor", "patch"]:
    """Infer bump type from commit types (FR-033)."""
    has_breaking = any(c.is_breaking for c in commits)
    has_feat = any(c.type == "feat" for c in commits)
    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    return "patch"


def _check_hard_failures(commits: list[CommitSummary]) -> list[HardFailure]:
    """Check for hard pipeline failures across commits (FR-036)."""
    failures: list[HardFailure] = []
    for c in commits:
        pipeline_raw = c.trailers.get("Pipeline", "")
        if not pipeline_raw:
            continue
        failed_stages: list[str] = []
        for entry in pipeline_raw.split(","):
            entry = entry.strip()
            if "=" in entry:
                stage, status = entry.split("=", 1)
                stage = stage.strip()
                status = status.strip()
                if stage in _HARD_STAGES and status == "fail":
                    failed_stages.append(stage)
        if failed_stages:
            failures.append(HardFailure(
                sha=c.short_sha,
                subject=c.subject,
                failed_stages=failed_stages,
            ))
    return failures


def prepare_release(
    *,
    repo_root: Path,
    bump_override: Literal["major", "minor", "patch"] | None = None,
) -> ReleaseContext:
    """Prepare a release context without executing changes.

    Args:
        repo_root: Repository root directory.
        bump_override: Override inferred bump type.

    Returns:
        :class:`ReleaseContext` with version info, commits, and failures.
    """
    current_version = _read_current_version(repo_root)

    # Find latest version tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_root),
        )
        if result.returncode == 0:
            last_tag = result.stdout.strip()
        else:
            last_tag = ""
    except Exception:
        last_tag = ""

    # Parse commits since last tag
    base = last_tag if last_tag else "HEAD~100"  # Fallback: last 100 commits
    commits = parse_commits(base=base, head="HEAD", repo_root=repo_root)

    # Infer or use override
    bump = bump_override or _infer_bump(commits)
    next_version = _bump_version(current_version, bump)

    # Check hard failures
    hard_failures = _check_hard_failures(commits)

    return ReleaseContext(
        current_version=current_version,
        next_version=next_version,
        bump_type=bump,
        commits=commits,
        has_breaking=any(c.is_breaking for c in commits),
        hard_failures=hard_failures,
        tag_name=f"v{next_version}",
    )


def execute_release(
    ctx: ReleaseContext,
    *,
    repo_root: Path,
    no_tag: bool = False,
) -> dict:
    """Execute the release: bump pyproject.toml, update changelog, create tag.

    Args:
        ctx: Prepared release context.
        repo_root: Repository root.
        no_tag: Skip creating git tag.

    Returns:
        Dict with execution results.
    """
    results = {
        "pyproject_updated": False,
        "changelog_updated": False,
        "tag_created": None,
    }

    # 1. Bump pyproject.toml
    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        # Replace version in [project] section
        new_content = re.sub(
            r'(version\s*=\s*")[^"]*(")',
            rf"\g<1>{ctx.next_version}\2",
            content,
            count=1,
        )
        if new_content != content:
            pyproject.write_text(new_content, encoding="utf-8")
            results["pyproject_updated"] = True

    # 2. Update changelog
    from dev_stack.vcs.changelog import generate_changelog
    cl_result = generate_changelog(
        repo_root=repo_root, unreleased=True
    )
    results["changelog_updated"] = cl_result.success

    # 3. Create annotated tag
    if not no_tag:
        try:
            tag_result = subprocess.run(
                ["git", "tag", "-a", ctx.tag_name, "-m", f"Release {ctx.tag_name}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo_root),
            )
            if tag_result.returncode == 0:
                results["tag_created"] = ctx.tag_name
        except Exception:
            pass

    return results
