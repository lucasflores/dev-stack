"""Integration tests for hooks lifecycle: init → status → modify → update → uninstall."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dev_stack.modules.vcs_hooks import VcsHooksModule
from dev_stack.pipeline.stages import FailureMode, StageResult, StageStatus


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create an actual git repository for integration tests."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        capture_output=True,
        cwd=tmp_path,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        capture_output=True,
        cwd=tmp_path,
    )

    # Create pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
        'commit-msg = true\npre-push = true\npre-commit = false\n'
    )

    # Create .dev-stack directory
    (tmp_path / ".dev-stack").mkdir(exist_ok=True)

    return tmp_path


class TestHooksLifecycle:
    """Full lifecycle: install → verify → status → modify → update → uninstall."""

    def test_full_lifecycle(self, git_repo: Path) -> None:
        module = VcsHooksModule(git_repo)

        # 1. Install
        install_result = module.install()
        assert install_result.success
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        assert (git_repo / ".git" / "hooks" / "pre-push").exists()

        # 2. Verify — healthy (but note constitution/instructions missing)
        manifest_path = git_repo / ".dev-stack" / "hooks-manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text())
        assert "commit-msg" in manifest_data["hooks"]
        assert "pre-push" in manifest_data["hooks"]

        # 3. Modify a hook
        hook = git_repo / ".git" / "hooks" / "commit-msg"
        original_content = hook.read_text()
        hook.write_text(original_content + "\n# modified by user")

        # 4. Update — should skip modified hook
        update_result = module.update()
        assert update_result.success
        assert any("manually modified" in w for w in update_result.warnings)

        # 5. Verify — should detect mismatch
        status = module.verify()
        assert "checksum mismatch" in (status.issue or "")

        # 6. Uninstall — should skip modified hook, remove matching hook
        uninstall_result = module.uninstall()
        assert uninstall_result.success
        # commit-msg was modified — should still exist
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        # pre-push was unmodified — should be deleted
        assert not (git_repo / ".git" / "hooks" / "pre-push").exists()
        # Manifest should be deleted
        assert not manifest_path.exists()

    def test_reinstall_overwrites_managed_hooks(self, git_repo: Path) -> None:
        module = VcsHooksModule(git_repo)

        module.install()
        # Second install should succeed (hooks are managed)
        result = module.install()
        assert result.success

    def test_install_with_no_pyproject_uses_defaults(self, git_repo: Path) -> None:
        """Without pyproject.toml, defaults enable commit-msg + pre-push."""
        (git_repo / "pyproject.toml").unlink()
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        assert (git_repo / ".git" / "hooks" / "commit-msg").exists()
        assert (git_repo / ".git" / "hooks" / "pre-push").exists()


class TestPrepareCommitMsgHookLifecycle:
    """Integration tests for the prepare-commit-msg hook."""

    def test_hook_installed_when_pre_commit_enabled(self, git_repo: Path) -> None:
        """prepare-commit-msg hook is installed alongside pre-commit."""
        # Enable pre-commit in config
        pyproject = git_repo / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[tool.dev-stack.hooks]\n'
            'commit-msg = true\npre-push = true\npre-commit = true\n'
        )
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        pcm_hook = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        assert pcm_hook.exists()
        # Verify it's in the manifest
        manifest_path = git_repo / ".dev-stack" / "hooks-manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        assert "prepare-commit-msg" in manifest_data["hooks"]

    def test_hook_not_installed_when_pre_commit_disabled(self, git_repo: Path) -> None:
        """prepare-commit-msg hook is NOT installed when pre-commit is disabled."""
        module = VcsHooksModule(git_repo)
        result = module.install()
        assert result.success
        pcm_hook = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        assert not pcm_hook.exists()

    def test_source_arg_skips_for_dash_m(self, git_repo: Path) -> None:
        """run_prepare_commit_msg_hook exits 0 when source='message'."""
        from dev_stack.vcs.hooks_runner import run_prepare_commit_msg_hook

        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("user message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="message")
        assert result == 0

    def test_source_arg_skips_for_amend(self, git_repo: Path) -> None:
        """run_prepare_commit_msg_hook exits 0 when source='commit'."""
        from dev_stack.vcs.hooks_runner import run_prepare_commit_msg_hook

        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("amend message\n")
        result = run_prepare_commit_msg_hook(str(msg_file), source="commit", commit_sha="abc123")
        assert result == 0


class TestPreCommitGraphFreshness:
    def _write_graph(self, repo_root: Path) -> None:
        graph_dir = repo_root / ".understand-anything"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "knowledge-graph.json").write_text(
            '{"project":{"name":"repo","analyzedAt":"2026-04-22T00:00:00Z","gitCommitHash":"abc"},"nodes":[{"filePath":"src/app.py"}]}',
            encoding="utf-8",
        )

    def _pass_stage(self, name: str) -> StageResult:
        return StageResult(
            stage_name=name,
            status=StageStatus.PASS,
            failure_mode=FailureMode.HARD,
            duration_ms=1,
            output="ok",
        )

    def test_pre_commit_blocks_when_graph_is_stale(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from dev_stack.vcs.hooks_runner import run_pre_commit_hook

        self._write_graph(git_repo)
        src_dir = git_repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text("print('changed')\n", encoding="utf-8")

        subprocess.run(["git", "add", "src/app.py", ".understand-anything/knowledge-graph.json"], cwd=git_repo, check=True)

        # Make graph stale by staging only source change after baseline graph commit.
        subprocess.run(["git", "commit", "-m", "chore: seed graph"], cwd=git_repo, check=True)
        (src_dir / "app.py").write_text("print('stale change')\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/app.py"], cwd=git_repo, check=True)

        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(
            "dev_stack.pipeline.stages._execute_lint_stage",
            lambda ctx: self._pass_stage("lint"),
        )
        monkeypatch.setattr(
            "dev_stack.pipeline.stages._execute_typecheck_stage",
            lambda ctx: self._pass_stage("typecheck"),
        )

        assert run_pre_commit_hook() == 1

    def test_pre_commit_passes_when_graph_update_is_staged(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from dev_stack.vcs.hooks_runner import run_pre_commit_hook

        self._write_graph(git_repo)
        src_dir = git_repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text("print('v1')\n", encoding="utf-8")

        subprocess.run(["git", "add", "src/app.py", ".understand-anything/knowledge-graph.json"], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "chore: seed graph"], cwd=git_repo, check=True)

        (src_dir / "app.py").write_text("print('v2')\n", encoding="utf-8")
        (git_repo / ".understand-anything" / "knowledge-graph.json").write_text(
            '{"project":{"name":"repo","analyzedAt":"2026-04-22T00:00:01Z","gitCommitHash":"def"},"nodes":[{"filePath":"src/app.py"}]}',
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "src/app.py", ".understand-anything/knowledge-graph.json"], cwd=git_repo, check=True)

        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(
            "dev_stack.pipeline.stages._execute_lint_stage",
            lambda ctx: self._pass_stage("lint"),
        )
        monkeypatch.setattr(
            "dev_stack.pipeline.stages._execute_typecheck_stage",
            lambda ctx: self._pass_stage("typecheck"),
        )

        assert run_pre_commit_hook() == 0
