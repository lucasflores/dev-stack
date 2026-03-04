"""Tests for individual pipeline stages."""
from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.pipeline.agent_bridge import AgentResponse
from dev_stack.pipeline.stages import (
    FailureMode,
    StageContext,
    StageResult,
    StageStatus,
    _execute_commit_stage,
    _execute_docs_narrative_stage,
    _execute_infra_sync_stage,
    build_pipeline_stages,
)


class _FakeAgent:
    def __init__(self, response: AgentResponse, *, available: bool = True) -> None:
        self._response = response
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def detect(self) -> str:
        return self._response.agent_cli

    def invoke(self, *_args, **_kwargs) -> AgentResponse:
        return self._response


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return tmp_path


def test_execute_commit_stage_writes_commit_message(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(
        success=True,
        content="feat(cli): add\n\n## Intent\nAdd stuff\n\n## Reasoning\nBecause\n\n## Scope\ncli\n\n## Narrative\nDone",
        json_data=None,
        agent_cli="claude",
        duration_ms=10,
    )
    context = StageContext(
        repo_root=repo_root,
        agent_bridge=_FakeAgent(response),
        completed_results=[
            StageResult("lint", StageStatus.PASS, FailureMode.HARD, 1),
            StageResult("test", StageStatus.PASS, FailureMode.HARD, 1),
        ],
    )
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "diff --git")
    monkeypatch.setattr("dev_stack.pipeline.stages._list_staged_files", lambda _path: ["src/app.py"])
    monkeypatch.setattr("dev_stack.pipeline.stages._detect_spec_ref", lambda _path: "specs/feature/spec.md")
    monkeypatch.setattr("dev_stack.pipeline.stages._detect_task_ref", lambda _path: "specs/feature/tasks.md")

    result = _execute_commit_stage(context)

    assert result.status == StageStatus.PASS, result.skipped_reason
    output_file = repo_root / ".git" / "COMMIT_EDITMSG"
    assert output_file.exists()
    contents = output_file.read_text(encoding="utf-8")
    assert "Spec-Ref: specs/feature/spec.md" in contents
    assert "Pipeline: lint=pass, test=pass" in contents


def test_execute_docs_narrative_stage_updates_guides(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(
        success=True,
        content="## Release Notes\nDocumented changes",
        json_data=None,
        agent_cli="claude",
        duration_ms=15,
    )
    context = StageContext(repo_root=repo_root, agent_bridge=_FakeAgent(response))
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "diff --git")

    result = _execute_docs_narrative_stage(context)

    guides_index = repo_root / "docs" / "guides" / "index.md"
    assert result.status == StageStatus.PASS
    assert guides_index.exists()
    assert "Documented changes" in guides_index.read_text(encoding="utf-8")


def test_execute_docs_narrative_stage_skips_when_template_missing(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(success=True, content="irrelevant", json_data=None, agent_cli="claude", duration_ms=1)
    context = StageContext(repo_root=repo_root, agent_bridge=_FakeAgent(response))
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "diff --git")
    missing_template = repo_root / "missing.txt"
    monkeypatch.setattr("dev_stack.pipeline.stages.PROMPT_TEMPLATE", missing_template)

    result = _execute_docs_narrative_stage(context)

    assert result.status == StageStatus.SKIP
    assert result.skipped_reason == "documentation template missing"


def test_execute_commit_stage_skips_without_diff(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(success=True, content="body", json_data=None, agent_cli="claude", duration_ms=1)
    context = StageContext(repo_root=repo_root, agent_bridge=_FakeAgent(response))
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "")
    monkeypatch.setattr("dev_stack.pipeline.stages._list_staged_files", lambda _path: ["src/app.py"])

    result = _execute_commit_stage(context)

    assert result.status == StageStatus.SKIP
    assert result.skipped_reason == "no staged changes detected"


def test_execute_commit_stage_skips_without_files(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(success=True, content="body", json_data=None, agent_cli="claude", duration_ms=1)
    context = StageContext(repo_root=repo_root, agent_bridge=_FakeAgent(response))
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "diff")
    monkeypatch.setattr("dev_stack.pipeline.stages._list_staged_files", lambda _path: [])

    result = _execute_commit_stage(context)

    assert result.status == StageStatus.SKIP
    assert result.skipped_reason == "no staged files detected"


def test_execute_commit_stage_warns_on_agent_failure(monkeypatch, repo_root: Path) -> None:
    response = AgentResponse(success=False, content="", json_data=None, agent_cli="claude", duration_ms=1, error="boom")
    context = StageContext(repo_root=repo_root, agent_bridge=_FakeAgent(response))
    monkeypatch.setattr("dev_stack.pipeline.stages._read_git_diff", lambda _path: "diff")
    monkeypatch.setattr("dev_stack.pipeline.stages._list_staged_files", lambda _path: ["src/app.py"])
    monkeypatch.setattr("dev_stack.pipeline.stages._detect_spec_ref", lambda _path: "specs/path/spec.md")
    monkeypatch.setattr("dev_stack.pipeline.stages._detect_task_ref", lambda _path: "specs/path/tasks.md")

    result = _execute_commit_stage(context)

    assert result.status == StageStatus.WARN
    assert "boom" in result.output


def test_execute_infra_sync_stage_detects_drift(repo_root: Path) -> None:
    hook_path = repo_root / "scripts" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("custom hook", encoding="utf-8")
    cfg_path = repo_root / ".pre-commit-config.yaml"
    cfg_path.write_text("custom config", encoding="utf-8")
    context = StageContext(repo_root=repo_root)

    result = _execute_infra_sync_stage(context)

    assert result.status == StageStatus.WARN
    assert "scripts/hooks/pre-commit" in result.output


def test_build_pipeline_stages_returns_eight_stages() -> None:
    stages = build_pipeline_stages()
    assert len(stages) == 8

    expected = [
        (1, "lint", FailureMode.HARD, False),
        (2, "typecheck", FailureMode.HARD, False),
        (3, "test", FailureMode.HARD, False),
        (4, "security", FailureMode.HARD, False),
        (5, "docs-api", FailureMode.HARD, False),
        (6, "docs-narrative", FailureMode.SOFT, True),
        (7, "infra-sync", FailureMode.SOFT, False),
        (8, "commit-message", FailureMode.SOFT, True),
    ]
    for stage, (order, name, mode, agent) in zip(stages, expected):
        assert stage.order == order
        assert stage.name == name
        assert stage.failure_mode == mode
        assert stage.requires_agent == agent