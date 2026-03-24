"""Tests for manifest helpers."""
from __future__ import annotations

from unittest.mock import patch

from dev_stack.manifest import AgentConfig, ModuleEntry, create_default, read_manifest, write_manifest


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


# --- US6: No machine-specific paths in committed config ---


def test_agent_config_to_dict_excludes_path() -> None:
    """T041: AgentConfig.to_dict() must NOT include a 'path' key."""
    agent = AgentConfig(cli="claude", path="/usr/local/bin/claude")

    result = agent.to_dict()

    assert "cli" in result
    assert "path" not in result


def test_agent_config_from_dict_ignores_legacy_path() -> None:
    """T042: from_dict with a legacy 'path' key sets path=None."""
    data = {"cli": "claude", "path": "/usr/local/bin/claude", "detected_at": "2025-01-01T00:00:00Z"}

    agent = AgentConfig.from_dict(data)

    assert agent.cli == "claude"
    assert agent.path is None


def test_manifest_round_trip_no_absolute_paths(tmp_path) -> None:
    """T043: Full manifest round-trip produces no absolute paths."""
    manifest = create_default(["hooks"])
    manifest.agent = AgentConfig(cli="claude", path="/usr/local/bin/claude")

    path = tmp_path / "dev-stack.toml"
    write_manifest(manifest, path)

    content = path.read_text()
    assert "/usr/local/bin" not in content

    loaded = read_manifest(path)
    assert loaded.agent.path is None


def test_runtime_agent_resolution_uses_shutil_which() -> None:
    """T046a: Agent path is resolved at runtime, not from stored value."""
    from dev_stack.config import detect_agent
    from dev_stack.manifest import StackManifest

    manifest = create_default(["hooks"])
    manifest.agent = AgentConfig(cli="claude", path=None)

    with patch("shutil.which", return_value="/resolved/bin/claude"):
        info = detect_agent(manifest)

    assert info.cli == "claude"
    assert info.path == "/resolved/bin/claude"