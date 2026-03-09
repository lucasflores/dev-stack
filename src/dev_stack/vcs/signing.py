"""SSH commit signing utilities.

Provides key detection, git version checking, commit-signing configuration,
and push-time unsigned-commit scanning.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from dev_stack.vcs import SigningConfig


# SSH public key patterns ordered by preference (ED25519 > ECDSA > RSA).
_KEY_PATTERNS = [
    "id_ed25519.pub",
    "id_ecdsa.pub",
    "id_rsa.pub",
]


@dataclass(slots=True)
class UnsignedCommit:
    """An agent-authored commit that is unsigned."""

    sha: str
    short_sha: str
    subject: str


# ------------------------------------------------------------------
# Key detection (FR-041)
# ------------------------------------------------------------------


def find_ssh_public_key() -> str | None:
    """Auto-detect an SSH public key in ``~/.ssh/``.

    Searches for common key filenames in preference order:
    ED25519 > ECDSA > RSA.

    Returns:
        Absolute path string to the key, or ``None`` if not found.
    """
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return None
    for pattern in _KEY_PATTERNS:
        candidate = ssh_dir / pattern
        if candidate.is_file():
            return str(candidate)
    return None


# ------------------------------------------------------------------
# Git version check (FR-040a)
# ------------------------------------------------------------------

_VERSION_RE = re.compile(r"(\d+)\.(\d+)")


def supports_ssh_signing() -> bool:
    """Return ``True`` if the installed git version is >= 2.34.

    SSH signing support was added in git 2.34.
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        m = _VERSION_RE.search(result.stdout)
        if not m:
            return False
        major, minor = int(m.group(1)), int(m.group(2))
        return (major, minor) >= (2, 34)
    except Exception:
        return False


# ------------------------------------------------------------------
# Configure signing (FR-039, FR-040)
# ------------------------------------------------------------------


def configure_ssh_signing(
    repo_root: Path,
    config: SigningConfig,
) -> tuple[bool, str]:
    """Set local git config for SSH commit signing.

    Args:
        repo_root: Repository root.
        config: Signing configuration from ``pyproject.toml``.

    Returns:
        ``(success, message)`` tuple.
    """
    if not config.enabled:
        return True, "Signing not enabled"

    if not supports_ssh_signing():
        return False, "SSH signing requires git >= 2.34; skipping"

    # Resolve key
    key_path = config.key or find_ssh_public_key()
    if key_path is None:
        return False, (
            "No SSH key detected. Generate one with: "
            "ssh-keygen -t ed25519 -C 'your_email@example.com'"
        )

    # Expand ~ and validate existence
    key_path_resolved = str(Path(key_path).expanduser())
    if not Path(key_path_resolved).is_file():
        return False, f"SSH key not found: {key_path_resolved}"

    # Set local git config entries
    settings = {
        "commit.gpgsign": "true",
        "gpg.format": "ssh",
        "user.signingkey": key_path_resolved,
    }

    try:
        for key, value in settings.items():
            subprocess.run(
                ["git", "config", "--local", key, value],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(repo_root),
            )
        return True, f"SSH signing configured with {key_path_resolved}"
    except Exception as exc:
        return False, f"Failed to configure signing: {exc}"


# ------------------------------------------------------------------
# Unsigned agent commit detection
# ------------------------------------------------------------------


def get_unsigned_agent_commits(
    local_sha: str,
    remote_sha: str,
    *,
    repo_root: Path | None = None,
) -> list[UnsignedCommit]:
    """Scan commits in push range for unsigned agent-authored commits.

    A commit is considered agent-authored if it contains an ``Agent:``
    trailer.  A commit is unsigned if ``%G?`` is not ``G`` (valid sig).

    Args:
        local_sha: Local (new) SHA.
        remote_sha: Remote (existing) SHA.
        repo_root: Optional repo root.

    Returns:
        List of unsigned agent commits.
    """
    if not local_sha or not remote_sha:
        return []

    # If remote_sha is all-zeros (new branch), check all commits
    null_sha = "0" * 40
    if remote_sha == null_sha:
        rev_range = local_sha
    else:
        rev_range = f"{remote_sha}..{local_sha}"

    sep = "---FIELD---"
    row_sep = "---ROW---"

    try:
        result = subprocess.run(
            [
                "git", "log", rev_range,
                f"--pretty=format:%H{sep}%h{sep}%s{sep}%b{sep}%G?{row_sep}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo_root) if repo_root else None,
        )
        if result.returncode != 0:
            return []
    except Exception:
        return []

    unsigned: list[UnsignedCommit] = []
    raw = result.stdout.strip()
    if not raw:
        return []

    for block in raw.split(row_sep):
        block = block.strip()
        if not block:
            continue
        parts = block.split(sep)
        if len(parts) < 5:
            continue
        sha, short_sha, subject, body, sig_status = (
            parts[0].strip(),
            parts[1].strip(),
            parts[2].strip(),
            parts[3].strip(),
            parts[4].strip(),
        )

        # Check if agent-authored (has Agent: trailer)
        is_agent = any(
            line.strip().startswith("Agent:")
            for line in body.splitlines()
        )
        if not is_agent:
            continue

        # Check if unsigned (G = valid signature)
        if sig_status != "G":
            unsigned.append(UnsignedCommit(
                sha=sha,
                short_sha=short_sha,
                subject=subject,
            ))

    return unsigned
