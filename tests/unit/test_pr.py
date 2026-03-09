"""Unit tests for PR description rendering — tests/unit/test_pr.py

Covers:
- Trailer aggregation: spec-refs, task-refs, agents, pipeline status
- Markdown rendering: all sections present
- Edge cases: no commits, no trailers
"""
from __future__ import annotations

import pytest

from dev_stack.vcs.commit_parser import CommitSummary
from dev_stack.vcs.pr import PRDescription, build_pr_description, render_pr_markdown


def _make_commit(
    sha: str = "abc1234567890",
    subject: str = "feat(cli): add pr command",
    ctype: str = "feat",
    scope: str | None = "cli",
    desc: str = "add pr command",
    trailers: dict[str, str] | None = None,
    is_breaking: bool = False,
    is_ai: bool = False,
    is_edited: bool = False,
) -> CommitSummary:
    return CommitSummary(
        sha=sha,
        short_sha=sha[:7],
        subject=subject,
        type=ctype,
        scope=scope,
        description=desc,
        trailers=trailers or {},
        is_breaking=is_breaking,
        is_ai_authored=is_ai,
        is_human_edited=is_edited,
        is_signed=False,
    )


class TestBuildPRDescription:
    """Test trailer aggregation logic."""

    def test_basic_aggregation(self) -> None:
        commits = [
            _make_commit(
                sha="aaa1111",
                is_ai=True,
                trailers={
                    "Agent": "claude",
                    "Spec-Ref": "specs/004/spec.md",
                    "Task-Ref": "specs/004/tasks.md#T001",
                    "Pipeline": "lint=pass,test=pass",
                },
            ),
            _make_commit(
                sha="bbb2222",
                is_ai=True,
                is_edited=True,
                trailers={
                    "Agent": "claude",
                    "Spec-Ref": "specs/004/spec.md",
                    "Task-Ref": "specs/004/tasks.md#T002",
                    "Pipeline": "lint=pass,test=fail",
                    "Edited": "true",
                },
            ),
            _make_commit(sha="ccc3333"),  # Manual commit, no trailers
        ]

        desc = build_pr_description(commits, branch="feat/my-feature", base="main")

        assert desc.total_commits == 3
        assert desc.ai_commits == 2
        assert desc.edited_count == 1
        assert "specs/004/spec.md" in desc.spec_refs
        assert len(desc.spec_refs) == 1  # Deduplicated
        assert len(desc.task_refs) == 2
        assert desc.agents == ["claude"]
        # Pipeline: test had pass + fail → worst is fail
        assert desc.pipeline_status["test"] == "fail"
        assert desc.pipeline_status["lint"] == "pass"

    def test_no_commits(self) -> None:
        desc = build_pr_description([], branch="feat/x")
        assert desc.total_commits == 0
        assert desc.ai_commits == 0
        assert desc.summary == "No changes"

    def test_no_trailers(self) -> None:
        commits = [_make_commit(), _make_commit(sha="def4567")]
        desc = build_pr_description(commits)
        assert desc.spec_refs == []
        assert desc.task_refs == []
        assert desc.agents == []
        # All stages should be n/a
        assert all(v == "n/a" for v in desc.pipeline_status.values())

    def test_multiple_agents(self) -> None:
        commits = [
            _make_commit(sha="a1", is_ai=True, trailers={"Agent": "claude"}),
            _make_commit(sha="a2", is_ai=True, trailers={"Agent": "copilot"}),
        ]
        desc = build_pr_description(commits)
        assert sorted(desc.agents) == ["claude", "copilot"]

    def test_pipeline_worst_case(self) -> None:
        commits = [
            _make_commit(sha="p1", trailers={"Pipeline": "lint=pass,security=warn"}),
            _make_commit(sha="p2", trailers={"Pipeline": "lint=warn,security=pass"}),
        ]
        desc = build_pr_description(commits)
        assert desc.pipeline_status["lint"] == "warn"
        assert desc.pipeline_status["security"] == "warn"

    def test_title_from_first_commit(self) -> None:
        commits = [
            _make_commit(sha="t1", subject="feat: newest commit"),
            _make_commit(sha="t2", subject="fix: older commit"),
        ]
        desc = build_pr_description(commits)
        assert desc.title == "feat: newest commit"


class TestRenderPRMarkdown:
    """Test Markdown rendering output."""

    def test_all_sections_present(self) -> None:
        commits = [
            _make_commit(
                sha="r1",
                is_ai=True,
                trailers={
                    "Agent": "claude",
                    "Spec-Ref": "specs/004/spec.md",
                    "Pipeline": "lint=pass",
                },
            ),
        ]
        desc = build_pr_description(commits, branch="feat/test")
        md = render_pr_markdown(desc)

        assert "## Summary" in md
        assert "## Spec References" in md
        assert "## Task References" in md
        assert "## AI Provenance" in md
        assert "## Pipeline Status" in md
        assert "## Commits" in md

    def test_ai_provenance_numbers(self) -> None:
        commits = [
            _make_commit(sha="ap1", is_ai=True, trailers={"Agent": "claude"}),
            _make_commit(sha="ap2"),
        ]
        desc = build_pr_description(commits)
        md = render_pr_markdown(desc)

        assert "**Total commits**: 2" in md
        assert "**AI-authored**: 1 (50%)" in md
        assert "**Agents used**: claude" in md

    def test_commit_list_includes_emoji(self) -> None:
        commits = [
            _make_commit(sha="em1", is_ai=True, is_edited=True,
                         subject="feat: with both"),
        ]
        desc = build_pr_description(commits)
        md = render_pr_markdown(desc)

        assert "🤖" in md
        assert "✏️" in md

    def test_no_spec_refs_placeholder(self) -> None:
        desc = build_pr_description([_make_commit()])
        md = render_pr_markdown(desc)
        assert "_No spec references found._" in md

    def test_no_task_refs_placeholder(self) -> None:
        desc = build_pr_description([_make_commit()])
        md = render_pr_markdown(desc)
        assert "_No task references found._" in md
