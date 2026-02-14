"""Tests for commit trailer helpers."""
from __future__ import annotations

from dev_stack.pipeline import commit_format
from dev_stack.pipeline.commit_format import TrailerData


def test_extract_and_upsert_trailers_preserves_body() -> None:
    message = "feat(cli): add command\n\nBody text\n\nSpec-Ref: old/spec.md\nAgent: copilot\n"

    updated = commit_format.upsert_trailers(
        message,
        TrailerData(
            spec_ref="specs/new/spec.md",
            task_ref="specs/new/tasks.md",
            agent="claude",
            pipeline="lint=pass",
            edited=False,
        ),
    )

    body, trailers = commit_format.extract_trailers(updated)
    assert body == "feat(cli): add command\n\nBody text"
    assert trailers["Spec-Ref"][0] == "specs/new/spec.md"
    assert trailers["Task-Ref"][0] == "specs/new/tasks.md"
    assert trailers["Agent"][0] == "claude"
    assert trailers["Pipeline"][0] == "lint=pass"
    assert trailers["Edited"][0] == "false"


def test_format_trailers_handles_missing_values() -> None:
    rendered = commit_format.format_trailers(TrailerData(spec_ref="spec.md"))
    assert rendered.strip().splitlines() == ["Spec-Ref: spec.md"]


def test_upsert_trailers_preserves_existing_boolean_flags() -> None:
    message = "feat!: refactor\n\nEdited: yes\n"

    updated = commit_format.upsert_trailers(message, TrailerData(agent="claude"))

    assert "Edited: true" in updated


def test_upsert_trailers_discards_invalid_boolean_values() -> None:
    message = "fix: bug\n\nEdited: maybe\n"

    updated = commit_format.upsert_trailers(message, TrailerData(agent="copilot"))

    assert "Edited:" not in updated


def test_upsert_trailers_without_new_data_returns_body() -> None:
    message = "chore: tidy"

    updated = commit_format.upsert_trailers(message, TrailerData())

    assert updated.strip() == "chore: tidy"


def test_private_helpers_handle_missing_values() -> None:
    assert commit_format._first(None) is None  # type: ignore[attr-defined]
    assert commit_format._first([]) is None  # type: ignore[attr-defined]
    assert commit_format._parse_bool("unknown") is None  # type: ignore[attr-defined]