"""Integration tests for docs strictness behavior across pipeline execution."""
from __future__ import annotations

import subprocess
from pathlib import Path

import tomli_w

from dev_stack.pipeline.runner import PipelineRunner
from dev_stack.pipeline.stages import (
    FailureMode,
    PipelineStage,
    StageContext,
    StageResult,
    StageStatus,
    _execute_docs_api_stage,
)


def _write_pipeline_pyproject(repo_root: Path, *, strict_docs: bool) -> None:
    data = {
        "tool": {"dev-stack": {"pipeline": {"strict_docs": strict_docs}}},
        "project": {"name": "demo"},
    }
    (repo_root / "pyproject.toml").write_text(tomli_w.dumps(data), encoding="utf-8")


def _create_docs_pkg(repo_root: Path) -> None:
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    src_pkg = repo_root / "src" / "mypkg"
    src_pkg.mkdir(parents=True, exist_ok=True)
    (src_pkg / "__init__.py").write_text("", encoding="utf-8")


def _post_docs_stage(_: StageContext) -> StageResult:
    return StageResult(
        stage_name="post-docs",
        status=StageStatus.PASS,
        failure_mode=FailureMode.HARD,
        duration_ms=1,
        output="follow-up executed",
    )


def _build_pipeline_with_post_stage(repo_root: Path) -> PipelineRunner:
    stages = [
        PipelineStage(
            order=1,
            name="docs-api",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_execute_docs_api_stage,
        ),
        PipelineStage(
            order=2,
            name="post-docs",
            failure_mode=FailureMode.HARD,
            requires_agent=False,
            executor=_post_docs_stage,
        ),
    ]
    return PipelineRunner(repo_root, stages=stages)


def test_non_strict_warnings_continue_to_subsequent_stage(monkeypatch, tmp_path: Path) -> None:
    _write_pipeline_pyproject(tmp_path, strict_docs=False)
    _create_docs_pkg(tmp_path)

    monkeypatch.setattr(
        "dev_stack.pipeline.stages._tool_available_in_venv",
        lambda tool, root: True,
    )

    def fake_run(cmd, **kwargs):
        if cmd[:5] == ("python3", "-m", "sphinx", "-b", "html"):
            return subprocess.CompletedProcess(cmd, 0, "WARNING: non-fatal warning", "")
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    runner = _build_pipeline_with_post_stage(tmp_path)
    result = runner.run()

    assert result.success is True
    assert [r.stage_name for r in result.results] == ["docs-api", "post-docs"]
    assert result.results[0].status == StageStatus.PASS
    assert result.results[1].status == StageStatus.PASS


def test_strict_warning_failure_stops_pipeline(monkeypatch, tmp_path: Path) -> None:
    _write_pipeline_pyproject(tmp_path, strict_docs=True)
    _create_docs_pkg(tmp_path)

    monkeypatch.setattr(
        "dev_stack.pipeline.stages._tool_available_in_venv",
        lambda tool, root: True,
    )

    def fake_run(cmd, **kwargs):
        if cmd[:5] == ("python3", "-m", "sphinx", "-b", "html"):
            assert "-W" in cmd
            return subprocess.CompletedProcess(cmd, 1, "WARNING: treated as error", "")
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    runner = _build_pipeline_with_post_stage(tmp_path)
    result = runner.run()

    assert result.success is False
    assert [r.stage_name for r in result.results] == ["docs-api"]
    assert result.results[0].status == StageStatus.FAIL


def test_existing_makefile_unchanged_during_pipeline_run(monkeypatch, tmp_path: Path) -> None:
    _write_pipeline_pyproject(tmp_path, strict_docs=False)
    _create_docs_pkg(tmp_path)

    makefile = tmp_path / "docs" / "Makefile"
    original = "SPHINXOPTS  ?= legacy-value\n"
    makefile.write_text(original, encoding="utf-8")

    monkeypatch.setattr(
        "dev_stack.pipeline.stages._tool_available_in_venv",
        lambda tool, root: True,
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr("subprocess.run", fake_run)

    runner = _build_pipeline_with_post_stage(tmp_path)
    result = runner.run()

    assert result.success is True
    assert makefile.read_text(encoding="utf-8") == original
