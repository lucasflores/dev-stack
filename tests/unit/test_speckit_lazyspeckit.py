"""Tests for SpecKitModule LazySpecKit integration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dev_stack.modules.speckit import (
    LAZYSPECKIT_PROMPT_RELATIVE_PATH,
    LAZYSPECKIT_REVIEWERS_DIR_NAME,
    SpecKitModule,
    _AGENCY_REVIEWER_MAP,
)


def _repo_with_git(tmp_path: Path) -> Path:
    repo = tmp_path / "speckit_repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def _fake_uv_install(*_args, **_kwargs):
    """Stub out uv tool install so tests don't need a real uv."""
    return None


class TestLazySpecKitInstall:
    def test_install_creates_prompt_file(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None):
            result = module.install(force=True)

        prompt = repo / LAZYSPECKIT_PROMPT_RELATIVE_PATH
        assert prompt.exists(), "LazySpecKit prompt was not installed"
        assert prompt.stat().st_size > 0

    def test_install_creates_vendored_reviewers(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None):
            module.install(force=True)

        reviewers_dir = repo / LAZYSPECKIT_REVIEWERS_DIR_NAME / "reviewers"
        assert reviewers_dir.is_dir()
        assert (reviewers_dir / "code-quality.md").exists()
        assert (reviewers_dir / "test.md").exists()

    def test_install_attempts_agency_downloads(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None) as mock_dl:
            module.install(force=True)

        assert mock_dl.call_count == len(_AGENCY_REVIEWER_MAP)

    def test_install_warns_on_download_failure(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value="network error"):
            result = module.install(force=True)

        assert any("network error" in w for w in result.warnings)


class TestLazySpecKitUninstall:
    def test_uninstall_removes_prompt_and_reviewers(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None):
            module.install(force=True)
        result = module.uninstall()

        assert result.success
        assert not (repo / LAZYSPECKIT_PROMPT_RELATIVE_PATH).exists()
        assert not (repo / LAZYSPECKIT_REVIEWERS_DIR_NAME).exists()


class TestLazySpecKitVerify:
    def test_verify_healthy_with_all_artifacts(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None):
            module.install(force=True)

        status = module.verify()
        assert status.healthy

    def test_verify_unhealthy_without_prompt(self, tmp_path: Path) -> None:
        repo = _repo_with_git(tmp_path)
        module = SpecKitModule(repo)
        with patch.object(module, "_maybe_install_cli_with_uv", return_value=None), \
             patch.object(module, "_download_agency_reviewer", return_value=None):
            module.install(force=True)

        (repo / LAZYSPECKIT_PROMPT_RELATIVE_PATH).unlink()
        status = module.verify()
        assert not status.healthy
        assert "LazySpecKit prompt missing" in (status.issue or "")


class TestInjectNoInteractionHeader:
    def test_injects_after_frontmatter(self) -> None:
        content = "---\nname: test\n---\nBody text here"
        result = SpecKitModule._inject_no_interaction_header(content)
        lines = result.split("\n")
        # Find the closing --- and check next non-empty line has the header
        idx = None
        fence_count = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                fence_count += 1
                if fence_count == 2:
                    idx = i
                    break
        assert idx is not None
        # Next lines should be: empty, "> header", empty
        assert lines[idx + 1] == ""
        assert lines[idx + 2].startswith("> **You are a REVIEWER")
        assert lines[idx + 3] == ""
