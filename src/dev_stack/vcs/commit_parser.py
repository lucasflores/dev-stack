"""Commit log parser — extracts structured CommitSummary from git log.

Provides :func:`parse_commits` which shells out to ``git log`` and
returns a list of :class:`CommitSummary` dataclasses.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CommitSummary:
    """Structured representation of a single git commit."""

    sha: str
    short_sha: str
    subject: str
    type: str
    scope: str | None
    description: str
    trailers: dict[str, str] = field(default_factory=dict)
    is_breaking: bool = False
    is_ai_authored: bool = False
    is_human_edited: bool = False
    is_signed: bool = False


# Regex matching conventional commit subjects.
_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<bang>!)?"
    r":\s*(?P<desc>.+)$"
)

# Separator used by git log --format
_SEP = "---GIT-LOG-SEP---"
_FIELD_SEP = "---FIELD---"


def parse_commits(
    base: str = "main",
    head: str = "HEAD",
    *,
    repo_root: Path | None = None,
) -> list[CommitSummary]:
    """Parse commits between *base* and *head* into summaries.

    Args:
        base: Base branch or commit ref (default ``"main"``).
        head: Head ref (default ``"HEAD"``).
        repo_root: Optional repo root for ``cwd``.

    Returns:
        List of :class:`CommitSummary` in reverse-chronological order
        (newest first), matching ``git log`` default.
    """
    # Format: sha, subject, body (includes trailers), signature status
    fmt = f"%H{_FIELD_SEP}%s{_FIELD_SEP}%b{_FIELD_SEP}%G?{_SEP}"

    cmd = [
        "git", "log", f"{base}..{head}",
        f"--pretty=format:{fmt}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(repo_root) if repo_root else None,
    )

    if result.returncode != 0:
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    entries = [e.strip() for e in raw.split(_SEP) if e.strip()]
    summaries: list[CommitSummary] = []

    for entry in entries:
        parts = entry.split(_FIELD_SEP)
        if len(parts) < 4:
            continue

        sha = parts[0].strip()
        subject = parts[1].strip()
        body = parts[2].strip()
        sig_status = parts[3].strip()

        # Parse conventional commit subject
        m = _CONVENTIONAL_RE.match(subject)
        if m:
            ctype = m.group("type")
            scope = m.group("scope")
            desc = m.group("desc")
            bang = bool(m.group("bang"))
        else:
            ctype = "other"
            scope = None
            desc = subject
            bang = False

        # Parse trailers from body
        trailers = _parse_trailers(body)

        # Determine flags
        is_breaking = bang or "BREAKING CHANGE" in body
        is_ai = "Agent" in trailers
        is_edited = trailers.get("Edited", "").lower() == "true"
        is_signed = sig_status == "G"

        summaries.append(
            CommitSummary(
                sha=sha,
                short_sha=sha[:7],
                subject=subject,
                type=ctype,
                scope=scope,
                description=desc,
                trailers=trailers,
                is_breaking=is_breaking,
                is_ai_authored=is_ai,
                is_human_edited=is_edited,
                is_signed=is_signed,
            )
        )

    return summaries


def _parse_trailers(body: str) -> dict[str, str]:
    """Extract key-value trailers from a commit body.

    Trailers are lines at the end of the body matching ``Key: value``.
    """
    if not body:
        return {}

    trailers: dict[str, str] = {}
    # Walk from the end; stop at the first non-trailer line
    lines = body.splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]+):\s*(.+)$", line)
        if m:
            trailers[m.group(1)] = m.group(2)
        else:
            break

    return trailers
