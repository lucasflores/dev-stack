"""Unit tests for dev_stack.vcs.scope — scope advisory check."""
from __future__ import annotations

import pytest

from dev_stack.vcs.scope import ScopeAdvisory, check_scope


class TestCheckScope:
    """Core scope advisory logic."""

    def test_empty_files_no_trigger(self) -> None:
        result = check_scope([])
        assert result.triggered is False
        assert result.reasons == []
        assert result.status == "pass"

    def test_single_dir_no_trigger(self) -> None:
        result = check_scope(["src/dev_stack/cli/main.py"])
        assert result.triggered is False

    def test_two_dirs_no_trigger(self) -> None:
        result = check_scope([
            "src/dev_stack/cli/main.py",
            "tests/unit/test_cli.py",
        ])
        assert result.triggered is False

    # --- Rule 1: 3+ root directories ---

    def test_three_root_dirs_triggers(self) -> None:
        result = check_scope([
            "src/dev_stack/cli/main.py",
            "tests/unit/test_cli.py",
            "specs/001/spec.md",
        ])
        assert result.triggered is True
        assert any("root directories" in r for r in result.reasons)
        assert result.status == "warn"

    def test_four_root_dirs_triggers(self) -> None:
        result = check_scope([
            "src/a.py",
            "tests/b.py",
            "specs/c.md",
            "docs/d.md",
        ])
        assert result.triggered is True

    # --- Rule 2: 3+ source subpackages ---

    def test_three_subpackages_triggers(self) -> None:
        result = check_scope([
            "src/dev_stack/cli/main.py",
            "src/dev_stack/modules/base.py",
            "src/dev_stack/pipeline/stages.py",
        ])
        assert result.triggered is True
        assert any("subpackages" in r for r in result.reasons)

    def test_two_subpackages_no_trigger(self) -> None:
        result = check_scope([
            "src/dev_stack/cli/main.py",
            "src/dev_stack/modules/base.py",
        ])
        assert result.triggered is False

    # --- Rule 3: specs + src overlap ---

    def test_specs_and_src_triggers(self) -> None:
        result = check_scope([
            "specs/001/spec.md",
            "src/dev_stack/cli/main.py",
        ])
        assert result.triggered is True
        assert any("specs/ and src/" in r for r in result.reasons)

    def test_specs_only_no_trigger(self) -> None:
        result = check_scope(["specs/001/spec.md"])
        assert result.triggered is False

    def test_src_only_no_trigger(self) -> None:
        result = check_scope(["src/dev_stack/cli/main.py"])
        assert result.triggered is False

    # --- Multiple rules ---

    def test_all_three_rules_fire(self) -> None:
        """All triggers can fire simultaneously."""
        result = check_scope([
            "src/dev_stack/cli/main.py",
            "src/dev_stack/modules/base.py",
            "src/dev_stack/pipeline/stages.py",
            "tests/unit/test_cli.py",
            "specs/001/spec.md",
        ])
        assert result.triggered is True
        assert len(result.reasons) == 3  # root dirs, subpackages, specs+src

    # --- Never blocking ---

    def test_never_blocks(self) -> None:
        """Scope advisory is informational — status is always 'warn' or 'pass'."""
        result = check_scope([
            "src/a/b/c.py",
            "src/a/d/e.py",
            "src/a/f/g.py",
            "tests/x.py",
            "specs/y.md",
            "docs/z.md",
        ])
        assert result.status in ("warn", "pass")


class TestScopeAdvisory:
    """ScopeAdvisory dataclass behavior."""

    def test_default_not_triggered(self) -> None:
        s = ScopeAdvisory()
        assert s.triggered is False
        assert s.status == "pass"

    def test_triggered_status(self) -> None:
        s = ScopeAdvisory(triggered=True, reasons=["test"])
        assert s.status == "warn"
