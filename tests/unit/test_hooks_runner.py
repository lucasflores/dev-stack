"""Tests for hooks_runner DEV_STACK_NO_HOOKS bypass."""

from __future__ import annotations

import io

from dev_stack.vcs.hooks_runner import (
    run_commit_msg_hook,
    run_pre_commit_hook,
    run_pre_push_hook,
    run_prepare_commit_msg_hook,
)


class TestDevStackNoHooksEnvVar:
    """All hook entry points exit 0 immediately when DEV_STACK_NO_HOOKS=1."""

    def test_commit_msg_hook_skips(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("DEV_STACK_NO_HOOKS", "1")
        assert run_commit_msg_hook(str(tmp_path / "nonexistent")) == 0

    def test_prepare_commit_msg_hook_skips(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("DEV_STACK_NO_HOOKS", "1")
        assert run_prepare_commit_msg_hook(str(tmp_path / "msg")) == 0

    def test_pre_push_hook_skips(self, monkeypatch) -> None:
        monkeypatch.setenv("DEV_STACK_NO_HOOKS", "1")
        assert run_pre_push_hook(io.StringIO("")) == 0

    def test_pre_commit_hook_skips(self, monkeypatch) -> None:
        monkeypatch.setenv("DEV_STACK_NO_HOOKS", "1")
        assert run_pre_commit_hook() == 0
