"""Unit tests for readme_injector."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_stack.visualization.readme_injector import (
    InjectionLedger,
    LedgerEntry,
    inject_diagram,
    inject_root_diagram,
    remove_diagram,
)


class TestInjectDiagram:
    def test_creates_managed_section_in_existing_readme(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nSome content.\n", encoding="utf-8")

        modified = inject_diagram(readme, "architecture", "graph LR\n  A --> B")

        assert modified is True
        text = readme.read_text(encoding="utf-8")
        assert "DEV-STACK:BEGIN:architecture" in text
        assert "DEV-STACK:END:architecture" in text
        assert "graph LR" in text
        assert "A --> B" in text

    def test_creates_readme_if_missing(self, tmp_path: Path) -> None:
        readme = tmp_path / "sub" / "README.md"
        assert not readme.exists()

        inject_diagram(readme, "component-architecture", "graph TD\n  X --> Y")

        assert readme.exists()
        text = readme.read_text(encoding="utf-8")
        assert "DEV-STACK:BEGIN:component-architecture" in text

    def test_idempotent_second_call(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# Title\n", encoding="utf-8")

        inject_diagram(readme, "architecture", "graph LR\n  A --> B")
        first = readme.read_text(encoding="utf-8")

        modified = inject_diagram(readme, "architecture", "graph LR\n  A --> B")
        second = readme.read_text(encoding="utf-8")

        assert modified is False
        assert first == second

    def test_permission_error_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# Title\n", encoding="utf-8")
        readme.chmod(0o444)  # read-only

        with caplog.at_level("WARNING"):
            modified = inject_diagram(readme, "architecture", "graph LR\n  A --> B")

        assert modified is False
        assert "Permission denied" in caplog.text

        # Cleanup permissions for tmp_path cleanup
        readme.chmod(0o644)


class TestRemoveDiagram:
    def test_removes_managed_section(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# Title\n", encoding="utf-8")

        inject_diagram(readme, "architecture", "graph LR\n  A --> B")
        assert "DEV-STACK:BEGIN:architecture" in readme.read_text(encoding="utf-8")

        removed = remove_diagram(readme, "architecture")
        assert removed is True

        text = readme.read_text(encoding="utf-8")
        assert "DEV-STACK:BEGIN:architecture" not in text
        assert "DEV-STACK:END:architecture" not in text
        assert "# Title" in text

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        assert remove_diagram(tmp_path / "nonexistent.md", "architecture") is False

    def test_returns_false_when_no_section(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# Title\n\nPlain content.\n", encoding="utf-8")

        assert remove_diagram(readme, "architecture") is False


class TestInjectionLedger:
    def test_load_returns_empty_when_missing(self, tmp_path: Path) -> None:
        ledger = InjectionLedger.load(tmp_path / "nonexistent.json")
        assert ledger.entries == []
        assert ledger.version == 1

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "ledger.json"
        ledger = InjectionLedger()
        ledger.add_entry("README.md", "architecture", component_name=None)
        ledger.add_entry("src/README.md", "component-architecture", component_name="Core")
        ledger.save(path)

        loaded = InjectionLedger.load(path)
        assert len(loaded.entries) == 2
        assert loaded.entries[0].readme_path == "README.md"
        assert loaded.entries[0].component_name is None
        assert loaded.entries[1].component_name == "Core"
        assert loaded.generated_at != ""

    def test_add_entry_deduplicates(self) -> None:
        ledger = InjectionLedger()
        ledger.add_entry("README.md", "architecture")
        ledger.add_entry("README.md", "architecture")
        assert len(ledger.entries) == 1

    def test_clear(self) -> None:
        ledger = InjectionLedger()
        ledger.add_entry("README.md", "architecture")
        ledger.clear()
        assert ledger.entries == []


class TestInjectRootDiagram:
    def test_injects_into_root_readme_and_updates_ledger(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")

        ledger = InjectionLedger()
        modified = inject_root_diagram(tmp_path, "graph LR\n  A --> B", ledger)

        assert modified is True
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "DEV-STACK:BEGIN:architecture" in text

        assert len(ledger.entries) == 1
        assert ledger.entries[0].readme_path == "README.md"
        assert ledger.entries[0].marker_id == "architecture"
        assert ledger.entries[0].component_name is None
