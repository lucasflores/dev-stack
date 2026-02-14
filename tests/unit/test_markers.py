"""Tests for marker read/write helpers."""
from __future__ import annotations

from pathlib import Path

from dev_stack.brownfield import markers


def test_write_and_read_managed_section(tmp_path) -> None:
    file_path = tmp_path / "config.py"

    changed = markers.write_managed_section(file_path, "hooks/config", "generated content")
    assert changed

    content = markers.read_managed_section(file_path, "hooks/config")
    assert content == "generated content"

    # Writing identical content should be a no-op
    changed_again = markers.write_managed_section(file_path, "hooks/config", "generated content")
    assert not changed_again


def test_block_comment_markers(tmp_path) -> None:
    file_path = tmp_path / "README.md"

    markers.write_managed_section(file_path, "docs/intro", "docs body")
    text = file_path.read_text(encoding="utf-8")

    assert "<!-- === DEV-STACK:BEGIN:docs/intro === -->" in text
    assert markers.read_managed_section(file_path, "docs/intro") == "docs body"
