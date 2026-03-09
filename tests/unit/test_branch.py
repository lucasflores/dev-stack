"""Unit tests for branch name validation — tests/unit/test_branch.py

Covers:
- Default pattern: valid and invalid branch names
- Custom pattern: overriding the default regex
- Exempt list: branches that bypass pattern check
- Spec-kit branch mismatch warning
- Edge cases: empty string, slashes, uppercase
"""
from __future__ import annotations

import pytest

from dev_stack.vcs.branch import BranchValidationResult, validate_branch_name


class TestDefaultPattern:
    """Validate the default ``{type}/{slug}`` pattern."""

    @pytest.mark.parametrize(
        "branch",
        [
            "feat/my-feature",
            "fix/issue-42",
            "docs/readme-update",
            "style/lint-fixes",
            "refactor/extract-parser",
            "perf/query-cache",
            "test/add-snapshots",
            "build/upgrade-deps",
            "ci/github-actions",
            "chore/cleanup",
            "revert/bad-merge",
            "feat/003-codeboarding-viz",
            "fix/a",
            "feat/dots.are.ok",
            "feat/underscores_are_ok",
        ],
    )
    def test_valid_branches(self, branch: str) -> None:
        result = validate_branch_name(branch)
        assert result.ok is True
        assert result.status == "pass"
        assert result.message is None

    @pytest.mark.parametrize(
        "branch",
        [
            "my-random-branch",
            "feature/my-feature",  # "feature" not in type list
            "feat",  # missing slash + slug
            "feat/",  # empty slug
            "feat/My-Feature",  # uppercase
            "FEAT/ok",  # uppercase type
            "feat/my feature",  # space in slug
            "",
        ],
    )
    def test_invalid_branches(self, branch: str) -> None:
        result = validate_branch_name(branch)
        assert result.ok is False
        assert result.status == "fail"
        assert result.message is not None
        assert "does not match" in result.message


class TestExemptBranches:
    """Exempt branches bypass pattern validation entirely."""

    @pytest.mark.parametrize(
        "branch",
        ["main", "master", "develop", "staging", "production"],
    )
    def test_default_exempt_branches(self, branch: str) -> None:
        result = validate_branch_name(branch)
        assert result.ok is True
        assert result.status == "exempt"

    def test_custom_exempt_list(self) -> None:
        result = validate_branch_name("release", exempt=["release"])
        assert result.ok is True
        assert result.status == "exempt"

    def test_non_exempt_branch_still_validated(self) -> None:
        result = validate_branch_name("random-name", exempt=["main"])
        assert result.ok is False
        assert result.status == "fail"


class TestCustomPattern:
    """Custom regex patterns override the default."""

    def test_custom_pattern_accepts(self) -> None:
        # Allow any branch starting with "release/"
        result = validate_branch_name(
            "release/v1.2.3",
            pattern=r"^release/v\d+\.\d+\.\d+$",
        )
        assert result.ok is True
        assert result.status == "pass"

    def test_custom_pattern_rejects(self) -> None:
        result = validate_branch_name(
            "feat/something",
            pattern=r"^release/v\d+\.\d+\.\d+$",
        )
        assert result.ok is False
        assert result.status == "fail"


class TestSpecBranchMismatch:
    """Non-blocking warning when branch differs from spec declaration."""

    def test_spec_branch_matches(self) -> None:
        result = validate_branch_name(
            "feat/my-feature", spec_branch="feat/my-feature"
        )
        assert result.ok is True
        assert result.status == "pass"
        assert result.message is None

    def test_spec_branch_mismatch_warns(self) -> None:
        result = validate_branch_name(
            "feat/my-feature", spec_branch="feat/other-feature"
        )
        assert result.ok is True
        assert result.status == "warn"
        assert "does not match" in (result.message or "")
        assert "feat/other-feature" in (result.message or "")

    def test_spec_branch_none_no_warning(self) -> None:
        result = validate_branch_name("feat/my-feature", spec_branch=None)
        assert result.ok is True
        assert result.status == "pass"

    def test_exempt_branch_skips_spec_check(self) -> None:
        """Exempt branches don't even check spec mismatch."""
        result = validate_branch_name("main", spec_branch="feat/my-feature")
        assert result.ok is True
        assert result.status == "exempt"


class TestDetectSpecBranch:
    """Test _detect_spec_branch helper."""

    def test_detect_from_spec_file(self, tmp_path: "Path") -> None:
        from pathlib import Path

        from dev_stack.vcs.branch import _detect_spec_branch

        specs_dir = tmp_path / "specs" / "001-my-feature"
        specs_dir.mkdir(parents=True)
        spec_file = specs_dir / "spec.md"
        spec_file.write_text('**Branch**: `feat/my-feature`\n')

        assert _detect_spec_branch(tmp_path) == "feat/my-feature"

    def test_no_specs_dir_returns_none(self, tmp_path: "Path") -> None:
        from dev_stack.vcs.branch import _detect_spec_branch

        assert _detect_spec_branch(tmp_path) is None

    def test_no_branch_line_returns_none(self, tmp_path: "Path") -> None:
        from pathlib import Path

        from dev_stack.vcs.branch import _detect_spec_branch

        specs_dir = tmp_path / "specs" / "001-thing"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text("# Spec\nNo branch line here.\n")

        assert _detect_spec_branch(tmp_path) is None
