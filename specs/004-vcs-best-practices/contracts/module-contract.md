# Module Contract: VcsHooksModule

**Branch**: `004-vcs-best-practices` | **Date**: 2026-03-08

---

## VcsHooksModule Class

Extends `ModuleBase` in `src/dev_stack/modules/vcs_hooks.py`. Manages git hook lifecycle, constitutional practices templates, and optional SSH signing configuration.

```python
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from dev_stack.modules.base import ModuleBase, ModuleResult, ModuleStatus


@dataclass
class HookEntry:
    """Single hook record in the manifest."""
    checksum: str           # SHA-256 hex digest
    installed_at: str       # ISO 8601 timestamp
    template_version: str   # Version of the hook template


@dataclass
class HookManifest:
    """JSON ledger tracking all managed hooks."""
    version: str                       # Schema version ("1.0")
    created: str                       # ISO 8601
    updated: str                       # ISO 8601
    hooks: dict[str, HookEntry]        # hook_name -> entry

    def to_dict(self) -> dict[str, Any]:
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookManifest:
        ...


class VcsHooksModule(ModuleBase):
    """Manages git hooks, constitutional practices, and signing config."""

    NAME: str = "vcs_hooks"
    VERSION: str = "0.1.0"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = (
        ".git/hooks/commit-msg",
        ".git/hooks/pre-push",
        ".dev-stack/hooks-manifest.json",
        ".dev-stack/instructions.md",
        "constitution-template.md",
        "cliff.toml",
    )

    MANAGED_HEADER: str = "# managed by dev-stack — do not edit manually"

    def install(self, *, force: bool = False) -> ModuleResult:
        """Install managed hooks, constitutional templates, and optionally configure signing.

        Steps:
        1. Read VcsConfig from pyproject.toml
        2. For each enabled hook (commit-msg, pre-push, optionally pre-commit):
           a. Check if .git/hooks/<name> exists
           b. If exists and not managed by dev-stack: warn, skip (unless force)
           c. If exists and managed: overwrite
           d. Copy template, set chmod 0o755
           e. Record in HookManifest
        3. Write .dev-stack/hooks-manifest.json
        4. Generate constitution-template.md at repo root
        5. Generate .dev-stack/instructions.md
        6. Detect agent files, offer to inject managed sections
        7. Generate cliff.toml from template
        8. If signing.enabled: configure SSH signing via local git config

        Returns:
            ModuleResult with created/modified file lists.

        Raises:
            ConflictError: If force=False and unmanaged hooks exist at target paths.
        """
        ...

    def uninstall(self) -> ModuleResult:
        """Remove managed hooks and clear manifest.

        Steps:
        1. Load HookManifest
        2. For each hook in manifest:
           a. Compute current checksum of .git/hooks/<name>
           b. If matches manifest checksum: delete file
           c. If mismatch: warn, skip
        3. Delete .dev-stack/hooks-manifest.json
        4. Remove managed sections from agent files (if present)
        5. Optionally remove signing git config

        Returns:
            ModuleResult with deleted file lists.
        """
        ...

    def update(self) -> ModuleResult:
        """Update managed hooks if templates have changed.

        Steps:
        1. Load HookManifest
        2. For each hook in manifest:
           a. Compute current file checksum
           b. If matches manifest (unmodified): overwrite with new template, update manifest
           c. If mismatch (manually modified): warn, skip
        3. Update managed sections in agent files
        4. Re-generate cliff.toml if template version changed

        Returns:
            ModuleResult with modified file lists.
        """
        ...

    def verify(self) -> ModuleStatus:
        """Verify hooks are correctly installed and healthy.

        Checks:
        - .git/hooks/commit-msg exists and starts with MANAGED_HEADER
        - .git/hooks/pre-push exists and starts with MANAGED_HEADER
        - .dev-stack/hooks-manifest.json exists and is valid JSON
        - File checksums match manifest entries
        - constitution-template.md exists
        - .dev-stack/instructions.md exists

        Returns:
            ModuleStatus with health information.
        """
        ...
```

---

## Hook Runner Functions

Located at `src/dev_stack/vcs/hooks_runner.py`. Called by the thin hook wrappers in `.git/hooks/`.

```python
def run_commit_msg_hook(msg_file_path: str) -> int:
    """Validate a commit message file.

    Called by .git/hooks/commit-msg with sys.argv[1] (the message temp file path).

    Steps:
    1. Read message from msg_file_path
    2. Load VcsConfig from pyproject.toml (for any custom rule config)
    3. Create LintConfig with extra_path pointing to dev_stack.rules
    4. Run GitLinter.lint(message) with rules:
       - UC1: ConventionalCommitRule
       - UC2: TrailerPresenceRule
       - UC3: TrailerPathRule
       - UC4: PipelineFailureWarningRule
    5. If violations with severity ERROR: print errors, return 1
    6. If violations with severity WARNING only: print warnings, return 0
    7. If no violations: return 0

    Args:
        msg_file_path: Path to the git commit message temp file.

    Returns:
        Exit code: 0 for success, 1 for rejection.
    """
    ...


def run_pre_push_hook(stdin: IO[str]) -> int:
    """Validate branch names and optionally check commit signatures.

    Called by .git/hooks/pre-push with sys.stdin.

    Steps:
    1. Parse stdin for push info (local_ref, local_sha, remote_ref, remote_sha)
    2. Extract branch name from local_ref
    3. Load BranchConfig from pyproject.toml
    4. If branch name is in exempt list: skip validation
    5. Validate branch name against pattern regex
    6. If invalid: print error with expected pattern, return 1
    7. If signing enforcement enabled:
       a. Get commits in push range (local_sha..remote_sha)
       b. For each commit with Agent trailer: check if signed
       c. If enforcement="block" and unsigned agent commits: return 1
       d. If enforcement="warn" and unsigned agent commits: print warning
    8. Return 0

    Args:
        stdin: Standard input stream with push info lines.

    Returns:
        Exit code: 0 for success, 1 for rejection.
    """
    ...
```

---

## Configuration Loader

Located at `src/dev_stack/vcs/__init__.py`.

```python
@dataclass
class HooksConfig:
    commit_msg: bool = True
    pre_push: bool = True
    pre_commit: bool = False


@dataclass
class BranchConfig:
    pattern: str = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)/[a-z0-9._-]+$"
    exempt: list[str] = field(
        default_factory=lambda: ["main", "master", "develop", "staging", "production"]
    )


@dataclass
class SigningConfig:
    enabled: bool = False
    enforcement: str = "warn"   # "warn" or "block"
    key: str | None = None      # Path to SSH public key; auto-detected if None


@dataclass
class VcsConfig:
    hooks: HooksConfig = field(default_factory=HooksConfig)
    branch: BranchConfig = field(default_factory=BranchConfig)
    signing: SigningConfig = field(default_factory=SigningConfig)


def load_vcs_config(repo_root: Path) -> VcsConfig:
    """Load VCS configuration from pyproject.toml.

    Reads [tool.dev-stack.hooks], [tool.dev-stack.branch],
    [tool.dev-stack.signing] sections. Missing sections use defaults.

    Args:
        repo_root: Repository root containing pyproject.toml.

    Returns:
        VcsConfig with merged defaults and user overrides.
    """
    ...
```

---

## Signing Utilities

Located at `src/dev_stack/vcs/signing.py`.

```python
SSH_KEY_PREFERENCE: list[str] = [
    "id_ed25519.pub",
    "id_ecdsa.pub",
    "id_rsa.pub",
]

MINIMUM_GIT_VERSION: tuple[int, ...] = (2, 34, 0)


def get_git_version() -> tuple[int, ...]:
    """Parse git version from `git --version` output."""
    ...


def supports_ssh_signing() -> bool:
    """Return True if installed git version >= 2.34."""
    ...


def find_ssh_public_key() -> Path | None:
    """Auto-detect the preferred SSH public key.

    Searches ~/.ssh/ in preference order: ed25519 > ecdsa > rsa.
    Falls back to any .pub file if none of the preferred names exist.
    """
    ...


def configure_ssh_signing(repo_root: Path, config: SigningConfig) -> ModuleResult:
    """Configure local git settings for SSH signing.

    Sets:
    - commit.gpgsign = true
    - gpg.format = ssh
    - user.signingkey = <detected or configured key path>

    Skips with warning if:
    - git < 2.34
    - No SSH key found and none configured
    """
    ...


def is_commit_signed(sha: str) -> bool:
    """Check if a commit has a valid signature via git log --pretty=%G?."""
    ...


def get_unsigned_agent_commits(base: str, head: str) -> list[str]:
    """Return SHAs of agent-authored commits without valid signatures in range."""
    ...
```

---

## Module Registration

In `src/dev_stack/modules/__init__.py`:

```python
from dev_stack.modules.vcs_hooks import VcsHooksModule

register_module(VcsHooksModule)

# Updated default modules for greenfield init
DEFAULT_GREENFIELD_MODULES = ("uv_project", "sphinx_docs", "hooks", "vcs_hooks", "speckit")
```

---

## Error Handling

All VCS operations use existing `DevStackError` hierarchy:

| Error | When Raised | Exit Code |
|-------|-------------|-----------|
| `ConflictError` | Unmanaged hook exists at target path (no `--force`) | 3 |
| `DevStackError` | Git not found, `.git/` missing, invalid config | 1 |
| `ModuleResult(success=False)` | Soft failures (signing skipped, hook update skipped) | — (logged) |

**Principle**: Never raise uncaught exceptions. All errors produce clear, actionable messages (SC-007).
