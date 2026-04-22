"""Integration tests for the commit-message pipeline stage."""
from __future__ import annotations

import subprocess
from pathlib import Path

from dev_stack.pipeline import commit_format
from dev_stack.pipeline.agent_bridge import AgentResponse
from dev_stack.pipeline.stages import FailureMode, StageContext, StageResult, StageStatus, _execute_commit_stage


class _AgentDouble:
    """Deterministic agent bridge stand-in for integration testing."""

    def __init__(self, content: str, agent_cli: str = "claude") -> None:
        self._response = AgentResponse(
            success=True,
            content=content,
            json_data=None,
            agent_cli=agent_cli,
            duration_ms=25,
        )

    def is_available(self) -> bool:  # pragma: no cover - exercised indirectly
        return True

    def detect(self) -> str:  # pragma: no cover - trivial
        return self._response.agent_cli

    def invoke(self, *_args, **_kwargs) -> AgentResponse:  # pragma: no cover - trivial
        return self._response


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(("git", "init", str(repo_root)), check=True, capture_output=True)


def test_commit_stage_generates_structured_message(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    specs_dir = repo_root / "specs" / "alpha"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("Spec body", encoding="utf-8")
    (specs_dir / "tasks.md").write_text("Tasks body", encoding="utf-8")

    src_dir = repo_root / "src"
    src_dir.mkdir()
    (src_dir / "module.py").write_text("print('hello world')\n", encoding="utf-8")
    subprocess.run(("git", "-C", str(repo_root), "add", "src", "specs"), check=True)

    agent = _AgentDouble(
        """feat(pipeline): wire commit agent\n\n"
        "## Intent\nEnsure every commit captures reasoning.\n\n"
        "## Reasoning\nUse AgentBridge output with trailers.\n\n"
        "## Scope\nPipeline, templates.\n\n"
        "## Narrative\nSummarize the change for future agents.\n"
        """
    )
    context = StageContext(
        repo_root=repo_root,
        agent_bridge=agent,
        completed_results=[
            StageResult("lint", StageStatus.PASS, FailureMode.HARD, 1),
            StageResult("test", StageStatus.PASS, FailureMode.HARD, 1),
        ],
    )

    result = _execute_commit_stage(context)

    assert result.status == StageStatus.PASS, result.output
    editmsg = repo_root / ".git" / "COMMIT_EDITMSG"
    message = editmsg.read_text(encoding="utf-8")

    lines = message.strip().splitlines()
    assert len(lines[0]) <= 72
    for heading in ("## Intent", "## Reasoning", "## Scope", "## Narrative"):
        assert heading in message

    body, trailers = commit_format.extract_trailers(message)
    assert "feat(pipeline)" in body
    assert trailers["Spec-Ref"][0].endswith("specs/alpha/spec.md")
    assert trailers["Task-Ref"][0].endswith("specs/alpha/tasks.md")
    assert trailers["Agent"][0] == "claude"
    pipeline_tokens = {token.strip() for token in trailers["Pipeline"][0].split(",")}
    assert "lint=pass" in pipeline_tokens
    assert "test=pass" in pipeline_tokens