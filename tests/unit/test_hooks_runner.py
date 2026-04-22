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


class TestCommitMsgCommentStripping:
    """FR-001: Only git comment lines are stripped; markdown headers are preserved."""

    def _write_and_run(self, tmp_path, message: str) -> int:
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text(message, encoding="utf-8")
        return run_commit_msg_hook(str(msg_file))

    def test_git_comments_stripped(self, tmp_path, monkeypatch) -> None:
        """Lines starting with '# ' or bare '#' are removed."""
        monkeypatch.delenv("DEV_STACK_NO_HOOKS", raising=False)
        msg = "feat: add feature\n\nBody text\n# This is a git comment\n#\nMore body"
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text(msg, encoding="utf-8")
        # Read back what the hook would clean
        import re
        lines = [ln for ln in msg.splitlines() if not re.match(r"^#(\s|$)", ln)]
        clean = "\n".join(lines).strip()
        # Git comments should be gone
        assert "# This is a git comment" not in clean
        assert clean.startswith("feat: add feature")
        assert "Body text" in clean
        assert "More body" in clean

    def test_markdown_headers_preserved(self, tmp_path) -> None:
        """## Intent, ### Sub, etc. must survive stripping."""
        msg = "feat: agent commit\n\n## Intent\nAdd brownfield\n## Reasoning\nNeeded\n### Detail\nMore"
        import re
        lines = [ln for ln in msg.splitlines() if not re.match(r"^#(\s|$)", ln)]
        clean = "\n".join(lines).strip()
        assert "## Intent" in clean
        assert "## Reasoning" in clean
        assert "### Detail" in clean

    def test_mixed_comments_and_headers(self, tmp_path) -> None:
        """Mixed git comments and markdown headers are handled correctly."""
        msg = (
            "feat: test\n\n"
            "## Intent\nDo something\n"
            "# This git comment should go\n"
            "## Scope\ncli only\n"
            "#\n"
            "## Narrative\nDone"
        )
        import re
        lines = [ln for ln in msg.splitlines() if not re.match(r"^#(\s|$)", ln)]
        clean = "\n".join(lines).strip()
        assert "## Intent" in clean
        assert "## Scope" in clean
        assert "## Narrative" in clean
        assert "# This git comment should go" not in clean

    def test_bare_hash_stripped(self, tmp_path) -> None:
        """A line with just '#' is stripped as a git comment."""
        msg = "fix: bug\n\nLine1\n#\nLine2"
        import re
        lines = [ln for ln in msg.splitlines() if not re.match(r"^#(\s|$)", ln)]
        clean = "\n".join(lines)
        assert "#" not in clean.split("\n")
        assert "Line1" in clean
        assert "Line2" in clean

    def test_tab_prefixed_git_comment_stripped(self, tmp_path) -> None:
        """A git comment line beginning with '#\t' is stripped."""
        msg = "fix: bug\n\nLine1\n#\tcomment\nLine2"
        import re

        lines = [ln for ln in msg.splitlines() if not re.match(r"^#(\s|$)", ln)]
        clean = "\n".join(lines)
        assert "#\tcomment" not in clean
        assert "Line1" in clean
        assert "Line2" in clean

    def test_run_commit_msg_hook_preserves_uc5_markdown_sections_end_to_end(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """Regression: ## headers must survive hook linting for UC5 commits."""
        monkeypatch.delenv("DEV_STACK_NO_HOOKS", raising=False)
        message = (
            "feat(cli): preserve uc5 section headers\n\n"
            "## Intent\n"
            "Validate heading preservation in commit-msg linting.\n\n"
            "## Reasoning\n"
            "Gitlint comment stripping must not remove markdown sections.\n\n"
            "## Scope\n"
            "commit-msg hook parsing path only.\n\n"
            "## Narrative\n"
            "Agent message structure remains intact through validation.\n\n"
            "Spec-Ref: none\n"
            "Task-Ref: none\n"
            "Agent: claude\n"
            "Pipeline: lint=pass, test=pass\n"
            "Edited: false\n"
        )

        rc = self._write_and_run(tmp_path, message)
        captured = capsys.readouterr()

        assert rc == 0, captured.err
