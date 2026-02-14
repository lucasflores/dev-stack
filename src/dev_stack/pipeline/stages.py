"""Pipeline stage definitions and executors."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence

from ..manifest import StackManifest
from .agent_bridge import AgentBridge
from .commit_format import TrailerData, upsert_trailers

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROMPT_TEMPLATE = PACKAGE_ROOT / "templates" / "prompts" / "docs_update.txt"
COMMIT_PROMPT_TEMPLATE = PACKAGE_ROOT / "templates" / "prompts" / "commit_message.txt"
DOC_SECTION_BEGIN = "<!-- === DEV-STACK:DOCS:BEGIN === -->"
DOC_SECTION_END = "<!-- === DEV-STACK:DOCS:END === -->"


class FailureMode(str, Enum):
    """Indicates whether a stage is a hard or soft gate."""

    HARD = "hard"
    SOFT = "soft"


class StageStatus(str, Enum):
    """Represents the outcome of a pipeline stage."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass(slots=True)
class StageResult:
    """Result emitted by each pipeline stage."""

    stage_name: str
    status: StageStatus
    failure_mode: FailureMode
    duration_ms: int
    output: str = ""
    skipped_reason: str | None = None


@dataclass(slots=True)
class StageContext:
    """Execution context shared by all stages."""

    repo_root: Path
    manifest: StackManifest | None = None
    force: bool = False
    agent_bridge: AgentBridge | None = None
    completed_results: list[StageResult] | None = None

    def without_agent(self) -> StageContext:
        """Return a shallow copy without the agent bridge for parallel execution."""

        return StageContext(
            repo_root=self.repo_root,
            manifest=self.manifest,
            force=self.force,
            agent_bridge=None,
            completed_results=self.completed_results,
        )


StageExecutor = Callable[[StageContext], StageResult]


@dataclass(slots=True)
class PipelineStage:
    """A single pipeline stage definition."""

    order: int
    name: str
    failure_mode: FailureMode
    requires_agent: bool
    executor: StageExecutor


def build_pipeline_stages() -> list[PipelineStage]:
    """Return the default pipeline stage sequence."""

    return [
        PipelineStage(
            order=1,
            name="lint",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_lint_stage,
        ),
        PipelineStage(
            order=2,
            name="test",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_test_stage,
        ),
        PipelineStage(
            order=3,
            name="security",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_security_stage,
        ),
        PipelineStage(
            order=4,
            name="docs",
            failure_mode=FailureMode.SOFT,
            requires_agent=True,
            executor=_execute_docs_stage,
        ),
        PipelineStage(
            order=5,
            name="infra-sync",
            failure_mode=FailureMode.SOFT,
            requires_agent=False,
            executor=_execute_infra_sync_stage,
        ),
        PipelineStage(
            order=6,
            name="commit-message",
            failure_mode=FailureMode.SOFT,
            requires_agent=True,
            executor=_execute_commit_stage,
        ),
    ]


def _execute_lint_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    outputs: list[str] = []
    for command in (("ruff", "format", "--check", "."), ("ruff", "check", ".")):
        success, output = _run_command(command, context.repo_root)
        label = " ".join(command)
        outputs.append(f"$ {label}\n{output or 'ok'}")
        if not success:
            return StageResult(
                stage_name="lint",
                status=StageStatus.FAIL,
                failure_mode=FailureMode.HARD,
                duration_ms=_elapsed_ms(start),
                output="\n\n".join(outputs),
            )
    return StageResult(
        stage_name="lint",
        status=StageStatus.PASS,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output="\n\n".join(outputs),
    )


def _execute_test_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    tests_dir = context.repo_root / "tests"
    if not tests_dir.exists():
        return StageResult(
            stage_name="test",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            skipped_reason="tests directory missing",
        )
    success, output = _run_command(("pytest", "-q"), context.repo_root)
    status = StageStatus.PASS if success else StageStatus.FAIL
    return StageResult(
        stage_name="test",
        status=status,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output=output,
    )


def _execute_security_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    commands = [
        ("pip-audit", "--progress-spinner", "off"),
        ("detect-secrets", "scan", str(context.repo_root)),
    ]
    outputs: list[str] = []
    for command in commands:
        success, output = _run_command(command, context.repo_root)
        outputs.append(f"$ {' '.join(command)}\n{output or 'ok'}")
        if not success:
            return StageResult(
                stage_name="security",
                status=StageStatus.FAIL,
                failure_mode=FailureMode.HARD,
                duration_ms=_elapsed_ms(start),
                output="\n\n".join(outputs),
            )
    return StageResult(
        stage_name="security",
        status=StageStatus.PASS,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output="\n\n".join(outputs),
    )


def _execute_docs_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    agent = context.agent_bridge
    if agent is None or not agent.is_available():
        return StageResult(
            stage_name="docs",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="coding agent unavailable",
        )
    if not PROMPT_TEMPLATE.exists():
        return StageResult(
            stage_name="docs",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="documentation template missing",
        )
    diff_text = _read_git_diff(context.repo_root)
    if not diff_text.strip():
        return StageResult(
            stage_name="docs",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="no staged changes detected",
        )
    readme_path = context.repo_root / "README.md"
    if not readme_path.exists():
        readme_path.write_text("# Project Documentation\n\n", encoding="utf-8")
    existing_section = _read_managed_section(readme_path)
    prompt = _render_docs_prompt(diff_text, existing_section, context.repo_root.name)
    response = agent.invoke(prompt, json_output=False, timeout_seconds=120)
    if not response.success:
        message = response.error or response.content or "Documentation agent failed"
        return StageResult(
            stage_name="docs",
            status=StageStatus.WARN,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            output=message,
        )
    _write_managed_section(readme_path, response.content.strip())
    return StageResult(
        stage_name="docs",
        status=StageStatus.PASS,
        failure_mode=FailureMode.SOFT,
        duration_ms=_elapsed_ms(start),
        output=f"Updated documentation section in {readme_path.name}",
    )


def _execute_infra_sync_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    targets = [
        (
            PACKAGE_ROOT / "templates" / "hooks" / "pre-commit",
            context.repo_root / "scripts" / "hooks" / "pre-commit",
        ),
        (
            PACKAGE_ROOT / "templates" / "hooks" / "pre-commit-config.yaml",
            context.repo_root / ".pre-commit-config.yaml",
        ),
    ]
    drift: list[str] = []
    for template_path, destination in targets:
        if not destination.exists():
            continue
        template_hash = _hash_file(template_path)
        dest_hash = _hash_file(destination)
        if template_hash != dest_hash:
            rel = destination.relative_to(context.repo_root)
            drift.append(str(rel))
    if drift:
        output = "Infrastructure drift detected in: " + ", ".join(sorted(drift))
        return StageResult(
            stage_name="infra-sync",
            status=StageStatus.WARN,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            output=output,
        )
    return StageResult(
        stage_name="infra-sync",
        status=StageStatus.PASS,
        failure_mode=FailureMode.SOFT,
        duration_ms=_elapsed_ms(start),
        output="Templates and installed files are in sync",
    )


def _execute_commit_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    agent = context.agent_bridge
    if agent is None or not agent.is_available():
        return StageResult(
            stage_name="commit-message",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="coding agent unavailable",
        )
    if not COMMIT_PROMPT_TEMPLATE.exists():
        return StageResult(
            stage_name="commit-message",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="commit message template missing",
        )

    diff_text = _read_git_diff(context.repo_root)
    staged_files = _list_staged_files(context.repo_root)
    if not diff_text.strip():
        return StageResult(
            stage_name="commit-message",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="no staged changes detected",
        )
    if not staged_files:
        return StageResult(
            stage_name="commit-message",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="no staged files detected",
        )

    agent_name = agent.detect()
    pipeline_summary = _format_pipeline_summary(context.completed_results or [])
    spec_ref = _detect_spec_ref(context.repo_root)
    task_ref = _detect_task_ref(context.repo_root)
    prompt = _render_commit_prompt(
        diff=diff_text,
        files=staged_files,
        repo_name=context.repo_root.name,
        pipeline_summary=pipeline_summary,
        spec_ref=spec_ref,
        task_ref=task_ref,
    )

    response = agent.invoke(prompt, json_output=False, timeout_seconds=180)
    if not response.success or not response.content.strip():
        message = response.error or response.content or "Agent returned empty commit message"
        return StageResult(
            stage_name="commit-message",
            status=StageStatus.WARN,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            output=message,
        )

    trailers = TrailerData(
        spec_ref=spec_ref,
        task_ref=task_ref,
        agent=agent_name,
        pipeline=pipeline_summary,
        edited=False,
    )
    commit_text = upsert_trailers(response.content.strip(), trailers)
    output_path = _write_commit_message(context.repo_root, commit_text)
    return StageResult(
        stage_name="commit-message",
        status=StageStatus.PASS,
        failure_mode=FailureMode.SOFT,
        duration_ms=_elapsed_ms(start),
        output=f"Wrote commit message via {agent_name} to {output_path.relative_to(context.repo_root)}",
    )


def _run_command(command: Sequence[str], cwd: Path) -> tuple[bool, str]:
    if not shutil.which(command[0]):
        return False, f"Command not found: {command[0]}"
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, f"Command not found: {command[0]}"
    output_parts = [part.strip() for part in (completed.stdout, completed.stderr) if part.strip()]
    output = "\n".join(output_parts)
    return completed.returncode == 0, output


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _read_git_diff(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ("git", "-C", str(repo_root), "diff", "--cached"),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _render_docs_prompt(diff: str, existing_section: str, repo_name: str) -> str:
    prompt = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    prompt = prompt.replace("{{REPO_NAME}}", repo_name)
    prompt = prompt.replace("{{DIFF}}", diff.strip() or "(no diff)")
    prompt = prompt.replace("{{EXISTING_SECTION}}", existing_section.strip() or "(empty)")
    return prompt


def _read_managed_section(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if DOC_SECTION_BEGIN in text and DOC_SECTION_END in text:
        before, remainder = text.split(DOC_SECTION_BEGIN, 1)
        section, _ = remainder.split(DOC_SECTION_END, 1)
        return section.strip()
    return ""


def _write_managed_section(path: Path, content: str) -> None:
    content = content.strip()
    if not path.exists():
        path.write_text(
            f"{DOC_SECTION_BEGIN}\n{content}\n{DOC_SECTION_END}\n",
            encoding="utf-8",
        )
        return
    text = path.read_text(encoding="utf-8")
    if DOC_SECTION_BEGIN in text and DOC_SECTION_END in text:
        before, remainder = text.split(DOC_SECTION_BEGIN, 1)
        _, after = remainder.split(DOC_SECTION_END, 1)
        new_text = f"{before}{DOC_SECTION_BEGIN}\n{content}\n{DOC_SECTION_END}{after}"
    else:
        if not text.endswith("\n"):
            text += "\n"
        new_text = f"{text}\n{DOC_SECTION_BEGIN}\n{content}\n{DOC_SECTION_END}\n"
    path.write_text(new_text, encoding="utf-8")


def _hash_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _render_commit_prompt(
    *,
    diff: str,
    files: Sequence[str],
    repo_name: str,
    pipeline_summary: str,
    spec_ref: str,
    task_ref: str,
) -> str:
    template = COMMIT_PROMPT_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{REPO_NAME}}": repo_name,
        "{{DIFF}}": diff.strip() or "(no diff)",
        "{{STAGED_FILES}}": "\n".join(files) if files else "(none)",
        "{{PIPELINE_SUMMARY}}": pipeline_summary or "(none)",
        "{{SPEC_REF}}": spec_ref or "(unknown)",
        "{{TASK_REF}}": task_ref or "(unknown)",
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def _list_staged_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ("git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _detect_spec_ref(repo_root: Path) -> str:
    env_value = os.getenv("DEV_STACK_SPEC_REF")
    if env_value:
        return env_value
    specs_dir = repo_root / "specs"
    if specs_dir.exists():
        matches = sorted(specs_dir.glob("**/spec.md"))
        if matches:
            try:
                return str(matches[0].relative_to(repo_root))
            except ValueError:
                return str(matches[0])
    return ""


def _detect_task_ref(repo_root: Path) -> str:
    env_value = os.getenv("DEV_STACK_TASK_REF")
    if env_value:
        return env_value
    specs_dir = repo_root / "specs"
    if specs_dir.exists():
        matches = sorted(specs_dir.glob("**/tasks.md"))
        if matches:
            try:
                return str(matches[0].relative_to(repo_root))
            except ValueError:
                return str(matches[0])
    return ""


def _format_pipeline_summary(results: Sequence[StageResult]) -> str:
    if not results:
        return ""
    return ", ".join(f"{result.stage_name}={result.status.value}" for result in results)


def _write_commit_message(repo_root: Path, commit_text: str) -> Path:
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    target = git_dir / "COMMIT_EDITMSG"
    target.write_text(commit_text.rstrip() + "\n", encoding="utf-8")
    return target
