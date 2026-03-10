"""Hook runner functions called by thin wrappers in ``.git/hooks/``.

Provides:
- ``run_commit_msg_hook(msg_file_path)`` — validates commit messages
- ``run_pre_push_hook(stdin)`` — validates branch names + signing
- ``run_pre_commit_hook()`` — runs lint + typecheck pipeline stages
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import IO

from dev_stack.vcs import load_vcs_config


def run_commit_msg_hook(msg_file_path: str) -> int:
    """Validate a commit message file using gitlint with custom rules.

    Called by ``.git/hooks/commit-msg`` with ``sys.argv[1]`` (the message
    temp file path).

    Steps:
        1. Read message from *msg_file_path*
        2. Load :class:`VcsConfig` from ``pyproject.toml``
        3. Create ``LintConfig`` with ``extra_path`` pointing to ``dev_stack.rules``
        4. Run ``GitLinter.lint(message)`` with rules UC1–UC4
        5. If violations with severity ERROR → print and return 1
        6. If violations with severity WARNING only → print warnings, return 0
        7. If no violations → return 0

    Args:
        msg_file_path: Path to the git commit message temp file.

    Returns:
        Exit code: 0 for success, 1 for rejection.
    """
    try:
        msg_path = Path(msg_file_path)
        if not msg_path.exists():
            print(f"Error: commit message file not found: {msg_file_path}", file=sys.stderr)
            return 1

        message = msg_path.read_text(encoding="utf-8")

        # Strip comment lines (git default comment char is '#')
        lines = [ln for ln in message.splitlines() if not ln.startswith("#")]
        clean_message = "\n".join(lines).strip()

        if not clean_message:
            print("Error: empty commit message", file=sys.stderr)
            return 1

        # Import gitlint components
        from gitlint.config import LintConfig
        from gitlint.git import GitContext
        from gitlint.lint import GitLinter

        # Find the rules package path
        import dev_stack.rules as rules_pkg

        rules_path = str(Path(rules_pkg.__file__).parent)

        # Build config programmatically — ignores any global .gitlint file
        config = LintConfig()
        config.set_general_option("ignore", "body-is-missing")
        config.set_rule_option("body-max-line-length", "line-length", 120)
        config.extra_path = rules_path

        linter = GitLinter(config)

        # Create a git context from the message string
        ctx = GitContext.from_commit_msg(clean_message)

        has_errors = False
        for commit in ctx.commits:
            violations = linter.lint(commit)
            for v in violations:
                # UC4 warnings are non-blocking (pipeline failure warnings)
                if v.rule_id == "UC4":
                    print(f"Warning [{v.rule_id}]: {v.message}", file=sys.stderr)
                else:
                    print(f"Error [{v.rule_id}]: {v.message}", file=sys.stderr)
                    has_errors = True

        return 1 if has_errors else 0

    except ImportError as exc:
        print(
            f"Error: gitlint-core is not installed. "
            f"Install it with: pip install gitlint-core\n  {exc}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error in commit-msg hook: {exc}", file=sys.stderr)
        return 1


def run_pre_push_hook(stdin: IO[str]) -> int:
    """Validate branch names and optionally check commit signatures.

    Called by ``.git/hooks/pre-push`` with ``sys.stdin``.

    Push info lines (from git) have the format::

        <local ref> <local sha> <remote ref> <remote sha>

    Steps:
        1. Determine the current branch name via ``git rev-parse``.
        2. Load :class:`VcsConfig` from ``pyproject.toml``.
        3. Call :func:`validate_branch_name` with config pattern + exemptions.
        4. Optionally detect spec-declared branch for mismatch warning.
        5. Return 1 (reject) if validation fails, 0 otherwise.

    Args:
        stdin: Standard input stream with push info lines.

    Returns:
        Exit code: 0 for success, 1 for rejection.
    """
    import subprocess

    try:
        repo_root = _get_repo_root()
        if repo_root is None:
            # Not in a git repo — nothing to validate
            return 0

        # Determine current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Detached HEAD or other edge case — skip validation
            return 0

        branch = result.stdout.strip()
        if not branch or branch == "HEAD":
            # Detached HEAD — skip
            return 0

        # Load config
        config = load_vcs_config(repo_root)

        # Detect spec branch (non-blocking heuristic)
        from dev_stack.vcs.branch import _detect_spec_branch, validate_branch_name

        spec_branch = _detect_spec_branch(repo_root)

        vr = validate_branch_name(
            branch,
            pattern=config.branch.pattern,
            exempt=config.branch.exempt,
            spec_branch=spec_branch,
        )

        if vr.status == "fail":
            print(f"Error [pre-push]: {vr.message}", file=sys.stderr)
            return 1

        if vr.status == "warn" and vr.message:
            print(f"Warning [pre-push]: {vr.message}", file=sys.stderr)

        # Check for unsigned agent commits if signing is enabled (US8)
        if config.signing.enabled:
            from dev_stack.vcs.signing import get_unsigned_agent_commits

            # Parse stdin for push refs: <local ref> <local sha> <remote ref> <remote sha>
            try:
                stdin_content = stdin.read()
            except Exception:
                stdin_content = ""

            for line in stdin_content.strip().splitlines():
                parts = line.split()
                if len(parts) < 4:
                    continue
                local_sha = parts[1]
                remote_sha = parts[3]

                unsigned = get_unsigned_agent_commits(
                    local_sha,
                    remote_sha,
                    repo_root=repo_root,
                )
                if unsigned:
                    msg_lines = [
                        f"{'Error' if config.signing.enforcement == 'block' else 'Warning'}"
                        f" [pre-push]: {len(unsigned)} unsigned agent commit(s):"
                    ]
                    for uc in unsigned:
                        msg_lines.append(f"  • {uc.short_sha} {uc.subject}")

                    for line_out in msg_lines:
                        print(line_out, file=sys.stderr)

                    if config.signing.enforcement == "block":
                        return 1

        return 0

    except Exception as exc:
        print(f"Error in pre-push hook: {exc}", file=sys.stderr)
        return 1


def run_pre_commit_hook() -> int:
    """Run lint and typecheck pipeline stages as a pre-commit check.

    Executes the first two pipeline stages (lint and typecheck) to catch
    issues before the commit is created.

    Returns:
        Exit code: 0 for success, 1 for rejection.
    """
    try:
        import subprocess

        repo_root = _get_repo_root()
        if repo_root is None:
            print(
                "Warning: could not detect repo root, skipping pre-commit checks", file=sys.stderr
            )
            return 0

        from dev_stack.pipeline.stages import (
            StageContext,
            StageStatus,
            build_pipeline_stages,
        )

        stages = build_pipeline_stages()
        # Run only lint (order=1) and typecheck (order=2)
        pre_commit_stages = [s for s in stages if s.name in ("lint", "typecheck")]

        ctx = StageContext(repo_root=repo_root)
        has_failures = False

        for stage in pre_commit_stages:
            result = stage.executor(ctx)
            if result.status == StageStatus.FAIL:
                print(
                    f"Error: pre-commit stage '{stage.name}' failed: {result.output}",
                    file=sys.stderr,
                )
                has_failures = True
            elif result.status == StageStatus.WARN:
                print(
                    f"Warning: pre-commit stage '{stage.name}': {result.output}",
                    file=sys.stderr,
                )

        return 1 if has_failures else 0

    except Exception as exc:
        print(f"Error in pre-commit hook: {exc}", file=sys.stderr)
        return 1


def _get_repo_root() -> Path | None:
    """Detect the git repository root via ``git rev-parse``."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
