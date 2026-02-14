"""Tests for dev_stack.config helpers."""
from __future__ import annotations

import sys

import pytest

from dev_stack import config
from dev_stack.config import assert_env_vars, detect_agent, ensure_agent_available, validate_env_vars
from dev_stack.errors import AgentUnavailableError, ConfigError
from dev_stack.manifest import create_default


def test_detect_agent_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("DEV_STACK_AGENT", "cursor")
    monkeypatch.setattr(
        config.shutil,
        "which",
        lambda name: "/opt/bin/cursor" if name == "cursor" else None,
    )

    info = detect_agent()

    assert info.cli == "cursor"
    assert info.path == "/opt/bin/cursor"


def test_detect_agent_uses_manifest(monkeypatch) -> None:
    monkeypatch.delenv("DEV_STACK_AGENT", raising=False)
    monkeypatch.setattr(config.shutil, "which", lambda _: None)

    manifest = create_default(["hooks"])
    manifest.agent.cli = "claude"
    manifest.agent.path = sys.executable

    info = detect_agent(manifest)

    assert info.cli == "claude"
    assert info.path == sys.executable


def test_detect_agent_priority_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DEV_STACK_AGENT", raising=False)

    def fake_which(name: str) -> str | None:
        return "/usr/local/bin/claude" if name == "claude" else None

    monkeypatch.setattr(config.shutil, "which", fake_which)

    info = detect_agent()

    assert info.cli == "claude"
    assert info.path == "/usr/local/bin/claude"


def test_ensure_agent_available_raises(monkeypatch) -> None:
    monkeypatch.delenv("DEV_STACK_AGENT", raising=False)
    monkeypatch.setattr(config.shutil, "which", lambda _: None)

    with pytest.raises(AgentUnavailableError):
        ensure_agent_available()


def test_validate_and_assert_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("DEV_STACK_PRESENT", "1")
    monkeypatch.delenv("DEV_STACK_MISSING", raising=False)

    result = validate_env_vars(["DEV_STACK_PRESENT", "DEV_STACK_MISSING"])
    assert result == {"DEV_STACK_PRESENT": True, "DEV_STACK_MISSING": False}

    with pytest.raises(ConfigError):
        assert_env_vars(["DEV_STACK_PRESENT", "DEV_STACK_MISSING"])
