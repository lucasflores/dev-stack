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
    """Return the default pipeline stage sequence.

    9-stage pipeline: lint → typecheck → test → security → docs-api →
    docs-narrative → infra-sync → visualize → commit-message.
    """

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
            name="typecheck",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_typecheck_stage,
        ),
        PipelineStage(
            order=3,
            name="test",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_test_stage,
        ),
        PipelineStage(
            order=4,
            name="security",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_security_stage,
        ),
        PipelineStage(
            order=5,
            name="docs-api",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_docs_api_stage,
        ),
        PipelineStage(
            order=6,
            name="docs-narrative",
            failure_mode=FailureMode.SOFT,
            requires_agent=True,
            executor=_execute_docs_narrative_stage,
        ),
        PipelineStage(
            order=7,
            name="infra-sync",
            failure_mode=FailureMode.SOFT,
            requires_agent=False,
            executor=_execute_infra_sync_stage,
        ),
        PipelineStage(
            order=8,
            name="visualize",
            failure_mode=FailureMode.SOFT,
            requires_agent=False,
            executor=_execute_visualize_stage,
        ),
        PipelineStage(
            order=9,
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


def _find_venv_site_packages(repo_root: Path) -> Path | None:
    """Return the site-packages directory inside a .venv, or None."""
    venv_lib = repo_root / ".venv" / "lib"
    if not venv_lib.is_dir():
        return None
    candidates = list(venv_lib.glob("python*/site-packages"))
    return candidates[0] if candidates else None


def _execute_security_stage(context: StageContext) -> StageResult:
    start = time.perf_counter()
    outputs: list[str] = []

    pip_audit_cmd: list[str] = ["pip-audit", "--progress-spinner", "off"]
    site_pkgs = _find_venv_site_packages(context.repo_root)
    if site_pkgs:
        pip_audit_cmd.extend(["--path", str(site_pkgs)])

    commands: list[tuple[str, ...]] = [
        tuple(pip_audit_cmd),
        ("detect-secrets", "scan", str(context.repo_root)),
    ]
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


def _execute_typecheck_stage(context: StageContext) -> StageResult:
    """Run mypy type checking against project source.

    Placeholder — real implementation wired in T016/T018.
    """
    start = time.perf_counter()
    if not shutil.which("mypy"):
        return StageResult(
            stage_name="typecheck",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            skipped_reason="mypy not found, skipping type check",
        )
    success, output = _run_command(
        ("python3", "-m", "mypy", "src/"),
        context.repo_root,
    )
    return StageResult(
        stage_name="typecheck",
        status=StageStatus.PASS if success else StageStatus.FAIL,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output=output,
    )


def _execute_docs_api_stage(context: StageContext) -> StageResult:
    """Run Sphinx apidoc + build for deterministic API docs."""
    import importlib.util

    start = time.perf_counter()

    # Graceful skip if Sphinx not installed
    has_sphinx = shutil.which("sphinx-build") is not None
    if not has_sphinx:
        has_sphinx = importlib.util.find_spec("sphinx") is not None
    if not has_sphinx:
        return StageResult(
            stage_name="docs-api",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            skipped_reason="sphinx not found, skipping API docs",
        )

    # Check docs/ directory exists
    docs_dir = context.repo_root / "docs"
    if not docs_dir.is_dir():
        return StageResult(
            stage_name="docs-api",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            skipped_reason="docs/ directory not found",
        )

    # Detect source package
    pkg_name = _detect_src_package(context.repo_root)
    if pkg_name is None:
        return StageResult(
            stage_name="docs-api",
            status=StageStatus.PASS,
            failure_mode=FailureMode.HARD,
            duration_ms=_elapsed_ms(start),
            output="No Python packages found in src/, nothing to document",
        )

    outputs: list[str] = []

    # Deterministic build environment
    env = {**os.environ, "SOURCE_DATE_EPOCH": "0"}

    # Step 1: Generate .rst stubs via sphinx-apidoc
    apidoc_cmd = (
        "python3",
        "-m",
        "sphinx.ext.apidoc",
        "-o",
        "docs/api",
        f"src/{pkg_name}",
        "-f",
        "--module-first",
        "-e",
    )
    try:
        apidoc_result = subprocess.run(
            apidoc_cmd,
            cwd=str(context.repo_root),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        apidoc_output = "\n".join(
            p.strip() for p in (apidoc_result.stdout, apidoc_result.stderr) if p.strip()
        )
        outputs.append(f"$ {' '.join(apidoc_cmd)}\n{apidoc_output or 'ok'}")
    except FileNotFoundError:
        outputs.append("sphinx.ext.apidoc not found")

    # Step 2: Build HTML
    build_cmd = (
        "python3",
        "-m",
        "sphinx",
        "-b",
        "html",
        "-W",
        "--keep-going",
        "docs",
        "docs/_build",
    )
    try:
        build_result = subprocess.run(
            build_cmd,
            cwd=str(context.repo_root),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        build_output = "\n".join(
            p.strip() for p in (build_result.stdout, build_result.stderr) if p.strip()
        )
        outputs.append(f"$ {' '.join(build_cmd)}\n{build_output or 'ok'}")
        success = build_result.returncode == 0
    except FileNotFoundError:
        outputs.append("sphinx build command not found")
        success = False

    return StageResult(
        stage_name="docs-api",
        status=StageStatus.PASS if success else StageStatus.FAIL,
        failure_mode=FailureMode.HARD,
        duration_ms=_elapsed_ms(start),
        output="\n\n".join(outputs),
    )


def _execute_docs_narrative_stage(context: StageContext) -> StageResult:
    """Invoke the coding agent to produce narrative documentation in ``docs/guides/``.

    This is a SOFT gate.  Agent unavailability results in SKIP, not FAIL.
    Narrative docs live exclusively in ``docs/guides/`` — API reference is
    handled by the deterministic ``docs-api`` stage.
    """
    start = time.perf_counter()
    agent = context.agent_bridge
    if agent is None or not agent.is_available():
        return StageResult(
            stage_name="docs-narrative",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="coding agent unavailable",
        )
    if not PROMPT_TEMPLATE.exists():
        return StageResult(
            stage_name="docs-narrative",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="documentation template missing",
        )
    diff_text = _read_git_diff(context.repo_root)
    if not diff_text.strip():
        return StageResult(
            stage_name="docs-narrative",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="no staged changes detected",
        )

    # Ensure docs/guides/ directory exists
    guides_dir = context.repo_root / "docs" / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)

    # Read existing narrative content (if managed section exists in guides)
    guides_index = guides_dir / "index.md"
    existing_section = ""
    if guides_index.exists():
        existing_section = guides_index.read_text(encoding="utf-8")

    prompt = _render_docs_prompt(diff_text, existing_section, context.repo_root.name)
    response = agent.invoke(prompt, json_output=False, timeout_seconds=120)
    if not response.success:
        message = response.error or response.content or "Documentation agent failed"
        return StageResult(
            stage_name="docs-narrative",
            status=StageStatus.WARN,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            output=message,
        )

    # Write agent output to docs/guides/
    guides_index.write_text(response.content.strip() + "\n", encoding="utf-8")
    return StageResult(
        stage_name="docs-narrative",
        status=StageStatus.PASS,
        failure_mode=FailureMode.SOFT,
        duration_ms=_elapsed_ms(start),
        output=f"Updated narrative documentation in docs/guides/",
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


def _is_visualization_enabled(context: StageContext) -> bool:
    """Check ``[tool.dev-stack.pipeline] visualize`` in pyproject.toml.  Default: True."""
    import tomllib

    pyproject = context.repo_root / "pyproject.toml"
    if not pyproject.exists():
        return True
    try:
        with open(pyproject, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("tool", {}).get("dev-stack", {}).get("pipeline", {}).get("visualize", True)
    except Exception:
        return True


def _execute_visualize_stage(context: StageContext) -> StageResult:
    """Run CodeBoarding analysis and inject Mermaid diagrams into READMEs.

    Soft gate — skips gracefully when CodeBoarding is absent or visualization
    is disabled via config.
    """
    start = time.perf_counter()

    if not _is_visualization_enabled(context):
        return StageResult(
            stage_name="visualize",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="visualization disabled in [tool.dev-stack.pipeline]",
        )

    # Check if visualization module is installed in the manifest
    if context.manifest and "visualization" not in (context.manifest.modules or {}):
        return StageResult(
            stage_name="visualize",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="visualization module not installed",
        )

    from ..visualization.codeboarding_runner import check_cli_available, run as cb_run
    from ..visualization.output_parser import parse_components
    from ..visualization.readme_injector import (
        InjectionLedger,
        inject_component_diagrams,
        inject_root_diagram,
    )

    if not check_cli_available():
        return StageResult(
            stage_name="visualize",
            status=StageStatus.SKIP,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            skipped_reason="CodeBoarding CLI not found — install with: pip install codeboarding",
        )

    outputs: list[str] = []
    try:
        result = cb_run(context.repo_root, incremental=True)
        outputs.append(f"CodeBoarding: {'ok' if result.success else 'failed'}")
        if not result.success:
            outputs.append(result.stderr or result.stdout)
            return StageResult(
                stage_name="visualize",
                status=StageStatus.FAIL,
                failure_mode=FailureMode.SOFT,
                duration_ms=_elapsed_ms(start),
                output="\n".join(outputs),
            )

        codeboarding_dir = context.repo_root / ".codeboarding"
        if not codeboarding_dir.is_dir():
            return StageResult(
                stage_name="visualize",
                status=StageStatus.WARN,
                failure_mode=FailureMode.SOFT,
                duration_ms=_elapsed_ms(start),
                output="CodeBoarding ran but .codeboarding/ directory not found",
            )

        components = parse_components(codeboarding_dir)
        ledger_path = context.repo_root / ".dev-stack" / "viz" / "injection-ledger.json"
        ledger = InjectionLedger.load(ledger_path)

        # Inject root architecture diagram from the first mermaid found
        root_mermaid = None
        for comp in components:
            if comp.mermaid:
                root_mermaid = comp.mermaid
                break

        if root_mermaid:
            inject_root_diagram(context.repo_root, root_mermaid, ledger)

        stats = inject_component_diagrams(context.repo_root, components, ledger)
        ledger.save(ledger_path)

        outputs.append(f"Diagrams injected: {stats.get('diagrams_injected', 0)}")
        outputs.append(f"READMEs modified: {len(stats.get('readmes_modified', []))}")

    except Exception as exc:
        outputs.append(f"Error: {exc}")
        return StageResult(
            stage_name="visualize",
            status=StageStatus.FAIL,
            failure_mode=FailureMode.SOFT,
            duration_ms=_elapsed_ms(start),
            output="\n".join(outputs),
        )

    return StageResult(
        stage_name="visualize",
        status=StageStatus.PASS,
        failure_mode=FailureMode.SOFT,
        duration_ms=_elapsed_ms(start),
        output="\n".join(outputs),
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

    # Scope advisory check (FR-044, FR-045, FR-046) — informational only
    from dev_stack.vcs.scope import check_scope

    scope_advisory = check_scope(staged_files)
    completed = list(context.completed_results or [])
    if scope_advisory.triggered:
        completed.append(
            StageResult(
                stage_name="scope-check",
                status=StageStatus.WARN,
                failure_mode=FailureMode.SOFT,
                duration_ms=0,
                output="; ".join(scope_advisory.reasons),
            )
        )

    pipeline_summary = _format_pipeline_summary(completed)
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


def _detect_src_package(repo_root: Path) -> str | None:
    """Find the first Python package under ``src/``.

    Scans ``repo_root / "src"`` for subdirectories containing an
    ``__init__.py`` file.  Returns the first match sorted alphabetically
    for determinism.  Returns ``None`` if no package is found or ``src/``
    does not exist.
    """
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return None
    candidates = sorted(
        d.name for d in src_dir.iterdir() if d.is_dir() and (d / "__init__.py").is_file()
    )
    return candidates[0] if candidates else None


def _build_venv_env(cwd: Path) -> dict[str, str] | None:
    """Build an env dict with ``.venv/bin`` prepended to PATH if a venv exists at *cwd*."""
    venv_bin = cwd / ".venv" / "bin"
    if not venv_bin.is_dir():
        return None
    env = {**os.environ}
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    env["VIRTUAL_ENV"] = str(cwd / ".venv")
    return env


def _run_command(command: Sequence[str], cwd: Path) -> tuple[bool, str]:
    env = _build_venv_env(cwd)
    if not shutil.which(command[0], path=env.get("PATH") if env else None):
        return False, f"Command not found: {command[0]}"
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=env,
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
            (
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACMRTUXB",
            ),
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
