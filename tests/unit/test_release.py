"""Unit tests for dev_stack.vcs.release — semantic release versioning."""
from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.vcs.commit_parser import CommitSummary
from dev_stack.vcs.release import (
    HardFailure,
    ReleaseContext,
    _bump_version,
    _check_hard_failures,
    _infer_bump,
    _read_current_version,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_commit(
    *,
    type: str = "fix",
    scope: str | None = None,
    desc: str = "something",
    is_breaking: bool = False,
    trailers: dict[str, str] | None = None,
    sha: str = "abcd1234abcd1234abcd1234abcd1234abcd1234",
) -> CommitSummary:
    return CommitSummary(
        sha=sha,
        short_sha=sha[:7],
        subject=f"{type}{'(' + scope + ')' if scope else ''}: {desc}",
        type=type,
        scope=scope,
        description=desc,
        trailers=trailers or {},
        is_breaking=is_breaking,
    )


# ---------------------------------------------------------------------------
# _read_current_version
# ---------------------------------------------------------------------------

class TestReadCurrentVersion:
    def test_reads_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "foo"\nversion = "2.3.4"\n')
        assert _read_current_version(tmp_path) == "2.3.4"

    def test_fallback_no_file(self, tmp_path: Path) -> None:
        assert _read_current_version(tmp_path) == "0.0.0"

    def test_fallback_no_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "foo"\n')
        assert _read_current_version(tmp_path) == "0.0.0"


# ---------------------------------------------------------------------------
# _bump_version
# ---------------------------------------------------------------------------

class TestBumpVersion:
    @pytest.mark.parametrize(
        "version,bump,expected",
        [
            ("1.2.3", "patch", "1.2.4"),
            ("1.2.3", "minor", "1.3.0"),
            ("1.2.3", "major", "2.0.0"),
            ("0.0.0", "patch", "0.0.1"),
            ("0.0.0", "minor", "0.1.0"),
            ("0.0.0", "major", "1.0.0"),
        ],
    )
    def test_bump(self, version: str, bump: str, expected: str) -> None:
        assert _bump_version(version, bump) == expected  # type: ignore[arg-type]

    def test_bad_version_fallback(self) -> None:
        assert _bump_version("invalid", "minor") == "0.1.0"


# ---------------------------------------------------------------------------
# _infer_bump
# ---------------------------------------------------------------------------

class TestInferBump:
    def test_breaking_is_major(self) -> None:
        commits = [_make_commit(type="fix", is_breaking=True)]
        assert _infer_bump(commits) == "major"

    def test_feat_is_minor(self) -> None:
        commits = [_make_commit(type="feat")]
        assert _infer_bump(commits) == "minor"

    def test_fix_only_is_patch(self) -> None:
        commits = [_make_commit(type="fix"), _make_commit(type="docs")]
        assert _infer_bump(commits) == "patch"

    def test_empty_is_patch(self) -> None:
        assert _infer_bump([]) == "patch"

    def test_breaking_beats_feat(self) -> None:
        commits = [
            _make_commit(type="feat"),
            _make_commit(type="fix", is_breaking=True),
        ]
        assert _infer_bump(commits) == "major"


# ---------------------------------------------------------------------------
# _check_hard_failures
# ---------------------------------------------------------------------------

class TestCheckHardFailures:
    def test_no_pipeline_trailers(self) -> None:
        commits = [_make_commit()]
        assert _check_hard_failures(commits) == []

    def test_passing_pipeline(self) -> None:
        commits = [_make_commit(trailers={"Pipeline": "lint=pass, test=pass"})]
        assert _check_hard_failures(commits) == []

    def test_soft_stage_fail_ignored(self) -> None:
        """Non-hard stages (e.g., format) don't count."""
        commits = [_make_commit(trailers={"Pipeline": "format=fail"})]
        assert _check_hard_failures(commits) == []

    def test_hard_stage_fail(self) -> None:
        commits = [_make_commit(
            trailers={"Pipeline": "lint=pass, typecheck=fail"},
            sha="abc1234" + "0" * 33,
        )]
        failures = _check_hard_failures(commits)
        assert len(failures) == 1
        assert failures[0].failed_stages == ["typecheck"]

    def test_multiple_hard_failures(self) -> None:
        commits = [_make_commit(
            trailers={"Pipeline": "lint=fail, test=fail, security=pass"},
        )]
        failures = _check_hard_failures(commits)
        assert len(failures) == 1
        assert set(failures[0].failed_stages) == {"lint", "test"}


# ---------------------------------------------------------------------------
# ReleaseContext
# ---------------------------------------------------------------------------

class TestReleaseContext:
    def test_construction(self) -> None:
        ctx = ReleaseContext(
            current_version="1.0.0",
            next_version="1.1.0",
            bump_type="minor",
            tag_name="v1.1.0",
        )
        assert ctx.tag_name == "v1.1.0"
        assert ctx.hard_failures == []
        assert ctx.commits == []
