"""Tests for hooks_runner DEV_STACK_NO_HOOKS bypass."""

from __future__ import annotations

import io
from pathlib import Path

from dev_stack.vcs.hooks_runner import (
    run_commit_msg_hook,
    run_pre_commit_hook,
    run_pre_push_hook,
    run_prepare_commit_msg_hook,
)


TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "dev_stack" / "templates" / "hooks"


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


class TestHookTemplateGuards:
    """Hook .py templates must check DEV_STACK_NO_HOOKS and catch ImportError."""

    HOOK_TEMPLATES = [
        "pre-commit.py",
        "prepare-commit-msg.py",
        "commit-msg.py",
        "pre-push.py",
    ]

    def test_templates_check_env_var_before_import(self) -> None:
        for name in self.HOOK_TEMPLATES:
            content = (TEMPLATE_DIR / name).read_text()
            env_pos = content.find("DEV_STACK_NO_HOOKS")
            import_pos = content.find("from dev_stack")
            assert env_pos != -1, f"{name} missing DEV_STACK_NO_HOOKS check"
            assert import_pos != -1, f"{name} missing dev_stack import"
            assert env_pos < import_pos, (
                f"{name}: DEV_STACK_NO_HOOKS check must come before dev_stack import"
            )

    def test_templates_catch_import_error(self) -> None:
        for name in self.HOOK_TEMPLATES:
            content = (TEMPLATE_DIR / name).read_text()
            assert "except ImportError" in content, (
                f"{name} must catch ImportError for graceful degradation"
            )
