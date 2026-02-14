"""Tests for manifest helpers."""
from __future__ import annotations

from dev_stack.manifest import ModuleEntry, create_default, read_manifest, write_manifest


def test_create_default_populates_modules() -> None:
    manifest = create_default(["hooks", "speckit", "visualization"])

    assert set(manifest.modules.keys()) == {"hooks", "speckit", "visualization"}
    assert manifest.agent.cli == "none"
    assert manifest.mode == "unknown"


def test_manifest_round_trip(tmp_path) -> None:
    manifest = create_default(["hooks"])
    manifest.modules["hooks"].config["stages"] = ["lint", "test"]
    manifest.mode = "greenfield"

    path = tmp_path / "dev-stack.toml"
    write_manifest(manifest, path)
    loaded = read_manifest(path)

    assert loaded.version == manifest.version
    assert loaded.modules["hooks"].config == {"stages": ["lint", "test"]}
    assert loaded.initialized == manifest.initialized
    assert loaded.mode == "greenfield"


def test_diff_modules_reports_added_and_updated() -> None:
    manifest = create_default(["hooks"])
    manifest.modules["hooks"].version = "0.0.1"
    latest = {
        "hooks": ModuleEntry(version="0.2.0", installed=True),
        "speckit": ModuleEntry(version="0.1.0", installed=True),
    }

    delta = manifest.diff_modules(latest, ["hooks", "speckit"])

    assert delta.updated == ["hooks"]
    assert delta.added == ["speckit"]
    assert delta.removed == []


def test_diff_modules_marks_removed_when_missing_from_latest() -> None:
    manifest = create_default(["hooks"])

    delta = manifest.diff_modules({}, ["hooks"])

    assert delta.removed == ["hooks"]
    assert not delta.added