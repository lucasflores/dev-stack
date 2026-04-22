"""Tests for HooksModule behavior."""
from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml

from dev_stack.errors import ConflictError
from dev_stack.modules import hooks
from dev_stack.modules.hooks import HooksModule, TEMPLATE_DIR


def _repo_with_git(tmp_path: Path) -> Path:
    repo = tmp_path / "hooks_repo"
    (repo / ".git" / "hooks").mkdir(parents=True)
    return repo


def test_install_creates_expected_files(tmp_path) -> None:
    repo = _repo_with_git(tmp_path)
    module = HooksModule(repo)

    result = module.install()

    assert result.success
    script = repo / "scripts" / "hooks" / "pre-commit"
    config = repo / ".pre-commit-config.yaml"
    git_hook = repo / ".git" / "hooks" / "pre-commit"
    for path in (script, config, git_hook):
        assert path.exists()
    assert script.stat().st_mode & stat.S_IXUSR
    assert git_hook.stat().st_mode & stat.S_IXUSR
    assert module.verify().healthy


def test_install_detects_conflicts(tmp_path) -> None:
    repo = _repo_with_git(tmp_path)
    module = HooksModule(repo)
    module.install()

    with pytest.raises(ConflictError):
        module.install()


def test_update_overwrites_changes(tmp_path) -> None:
    repo = _repo_with_git(tmp_path)
    module = HooksModule(repo)
    module.install()

    script = repo / "scripts" / "hooks" / "pre-commit"
    script.write_text("custom", encoding="utf-8")

    module.update()

    template_contents = (TEMPLATE_DIR / "pre-commit").read_text(encoding="utf-8")
    assert script.read_text(encoding="utf-8") == template_contents


def test_uninstall_and_verify_failure(tmp_path) -> None:
    repo = _repo_with_git(tmp_path)
    module = HooksModule(repo)
    module.install()

    module.uninstall()

    assert module.verify().healthy is False


def test_write_pre_commit_config_replaces_invalid_repos_type(tmp_path: Path) -> None:
    """Malformed repos content should not be coerced into invalid list entries."""
    config_path = tmp_path / ".pre-commit-config.yaml"
    config_path.write_text("repos: not-a-list\n", encoding="utf-8")

    hooks._write_pre_commit_config(config_path, hooks._build_hook_list())

    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    assert isinstance(loaded.get("repos"), list)
    repos = loaded["repos"]
    assert all(isinstance(repo, dict) for repo in repos)
    assert any(repo.get("repo") == "local" for repo in repos)


def test_module_base_marker_helpers(tmp_path) -> None:
    repo = _repo_with_git(tmp_path)
    module = HooksModule(repo)

    relative = Path("docs") / "example.md"
    first_write = module.write_managed_section(relative, "INTRO", "managed content")
    assert first_write is True

    read_back = module.read_managed_section(relative, "INTRO")
    assert read_back == "managed content"

    second_write = module.write_managed_section(relative, "INTRO", "managed content")
    assert second_write is False
