"""Hook runner functions called by thin wrappers in ``.git/hooks/``.

Provides:
- ``run_commit_msg_hook(msg_file_path)`` — validates commit messages
- ``run_pre_push_hook(stdin)`` — validates branch names + signing
- ``run_pre_commit_hook()`` — runs lint + typecheck pipeline stages
- ``run_prepare_commit_msg_hook(message_file, source, commit_sha)`` — stages 3-9
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import IO

from dev_stack.vcs import load_vcs_config

logger = logging.getLogger(__name__)

# Sources where git already has a message — skip generation
_SKIP_SOURCES = frozenset({"message", "commit", "merge", "squash"})


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
    if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
        return 0
    try:
        msg_path = Path(msg_file_path)
        if not msg_path.exists():
            print(f"Error: commit message file not found: {msg_file_path}", file=sys.stderr)
            return 1

        message = msg_path.read_text(encoding="utf-8")

        # Strip git comment lines only (lines starting with "# " or bare "#").
        # Preserve markdown headers (##, ###, etc.) needed by UC5.
        import re
        lines = [ln for ln in message.splitlines() if not re.match(r"^# |^#$", ln)]
        clean_message = "\n".join(lines).strip()

        if not clean_message:
            print("Error: empty commit message", file=sys.stderr)
            return 1

        # Import gitlint components
        from gitlint.config import LintConfig
        from gitlint.git import GitCommit, GitCommitMessage, GitContext
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

        # Build commit context directly from already-cleaned message.
        # GitContext.from_commit_msg() strips all lines that start with '#',
        # which incorrectly removes markdown headings like "## Intent".
        lines = clean_message.splitlines()
        title = lines[0] if lines else ""
        body = lines[1:] if len(lines) > 1 else []

        ctx = GitContext()
        commit_msg_obj = GitCommitMessage(
            context=ctx,
            original=clean_message,
            full=clean_message,
            title=title,
            body=body,
        )
        ctx.commits.append(GitCommit(ctx, commit_msg_obj))

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


def run_prepare_commit_msg_hook(
    message_file: str,
    source: str | None = None,
    commit_sha: str | None = None,
) -> int:
    """Run pipeline stages 3-9 during the prepare-commit-msg hook.

    Args:
        message_file: Path to the commit message temp file (git's ``$1``).
        source: Message source from git's ``$2``:
            ``message``, ``template``, ``merge``, ``squash``, ``commit``, or ``None``.
        commit_sha: Commit SHA when source is ``commit`` (git's ``$3``).

    Returns:
        Exit code with differential semantics:
        - Stages 3-5 failure -> ``1`` (abort commit)
        - Stage 9 failure -> ``0`` (fallback to editor)
        - Message-file write errors -> ``0`` (allow editor fallback)
    """
    if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
        return 0

    # Normalize empty string to None
    if source is not None and not source.strip():
        source = None

    # Early exit: user already provided a message
    if source in _SKIP_SOURCES:
        logger.debug(
            "prepare-commit-msg: skip generation source=%s reason=user_provided", source
        )
        return 0

    logger.debug(
        "prepare-commit-msg: generating message_file=%s source=%s commit_sha=%s",
        message_file, source, commit_sha,
    )

    try:
        repo_root = _get_repo_root()
        if repo_root is None:
            print(
                "Warning: could not detect repo root, skipping prepare-commit-msg",
                file=sys.stderr,
            )
            return 0

        # Set hook context env vars for downstream stage filtering
        os.environ["DEV_STACK_HOOK_CONTEXT"] = "prepare-commit-msg"
        os.environ["DEV_STACK_MESSAGE_FILE"] = message_file

        from dev_stack.pipeline.runner import PipelineRunner
        from dev_stack.pipeline.stages import FailureMode, StageStatus

        runner = PipelineRunner(repo_root)
        result = runner.run()

        # Check for hard failures in stages 3-5 (test, security, docs-api)
        hard_stage_orders = {3, 4, 5}
        for stage_result in result.results:
            if (
                stage_result.status == StageStatus.FAIL
                and stage_result.failure_mode == FailureMode.HARD
            ):
                # Find the stage order from the pipeline definitions
                from dev_stack.pipeline.stages import build_pipeline_stages

                stage_defs = {s.name: s.order for s in build_pipeline_stages()}
                order = stage_defs.get(stage_result.stage_name, 0)
                if order in hard_stage_orders:
                    print(
                        f"Error: stage '{stage_result.stage_name}' failed: "
                        f"{stage_result.output}",
                        file=sys.stderr,
                    )
                    return 1

        # Find commit-message stage result and write to message file
        for stage_result in result.results:
            if (
                stage_result.stage_name == "commit-message"
                and stage_result.status == StageStatus.PASS
            ):
                # Read the generated message from COMMIT_EDITMSG
                editmsg = repo_root / ".git" / "COMMIT_EDITMSG"
                if editmsg.exists():
                    try:
                        generated = editmsg.read_text(encoding="utf-8")
                        msg_path = Path(message_file)
                        msg_path.write_text(generated, encoding="utf-8")
                        logger.debug(
                            "prepare-commit-msg: wrote message to %s", message_file
                        )
                    except (PermissionError, OSError) as exc:
                        logger.warning(
                            "prepare-commit-msg: failed to write message file: %s", exc
                        )
                        print(
                            f"Warning: could not write commit message: {exc}",
                            file=sys.stderr,
                        )
                        return 0
                break

        return 0

    except Exception as exc:
        logger.warning("prepare-commit-msg: unexpected error: %s", exc)
        print(f"Warning: prepare-commit-msg hook error: {exc}", file=sys.stderr)
        return 0


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
    if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
        return 0

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
    if os.environ.get("DEV_STACK_NO_HOOKS") == "1":
        return 0

    try:
        repo_root = _get_repo_root()
        if repo_root is None:
            print(
                "Warning: could not detect repo root, skipping pre-commit checks",
                file=sys.stderr,
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
