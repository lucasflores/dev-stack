"""Tests for hook generation.

Covers:
- _build_hook_list → pipeline + ruff + pytest + mypy (always Python)
- _render_pre_commit_config → YAML with managed section markers
- User hook preservation outside managed section
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dev_stack.modules.hooks import HookEntry, _build_hook_list, _render_pre_commit_config


def test_build_hook_list_includes_all_python_hooks() -> None:
    """_build_hook_list always returns pipeline + ruff + pytest + mypy."""
    hooks = _build_hook_list()

    ids = [h.id for h in hooks]
    assert ids == ["dev-stack-pipeline", "dev-stack-ruff", "dev-stack-pytest", "dev-stack-mypy"]


def test_render_pre_commit_config_has_yaml_structure() -> None:
    """Rendered YAML has proper repos/hooks structure."""
    hooks = _build_hook_list()

    yaml_str = _render_pre_commit_config(hooks)

    assert "repos:" in yaml_str
    assert "repo: local" in yaml_str
    assert "dev-stack-pipeline" in yaml_str


def test_managed_section_markers_applied(tmp_path: Path) -> None:
    """After write_managed_section, file contains markers."""
    from dev_stack.brownfield.markers import write_managed_section

    hooks = _build_hook_list()
    rendered = _render_pre_commit_config(hooks)

    config_path = tmp_path / ".pre-commit-config.yaml"
    write_managed_section(config_path, "HOOKS", rendered)

    content = config_path.read_text()
    assert "DEV-STACK:BEGIN:HOOKS" in content
    assert "DEV-STACK:END:HOOKS" in content


def test_user_hooks_preserved_outside_managed_section(tmp_path: Path) -> None:
    """Existing repos and local repo user hooks survive re-init via YAML merge."""
    config_path = tmp_path / ".pre-commit-config.yaml"
    user_content = (
        "repos:\n"
        "  - repo: https://github.com/user/custom-hook\n"
        "    rev: v1.0\n"
        "    hooks:\n"
        "      - id: my-custom-hook\n"
    )
    config_path.write_text(user_content)

    from dev_stack.modules.hooks import _build_hook_list, _write_pre_commit_config

    hooks = _build_hook_list()
    _write_pre_commit_config(config_path, hooks)

    result = yaml.safe_load(config_path.read_text())

    # The file must be valid YAML with a single top-level repos: key.
    assert isinstance(result.get("repos"), list)
    repos_text = config_path.read_text()
    assert repos_text.count("repos:") == 1, "Must not produce duplicate top-level repos: keys"

    # User's external repo must be preserved.
    repo_urls = [r.get("repo") for r in result["repos"] if isinstance(r, dict)]
    assert "https://github.com/user/custom-hook" in repo_urls

    # Dev-stack pipeline hook must be present in the local repo.
    local_repo = next(
        (r for r in result["repos"] if isinstance(r, dict) and r.get("repo") == "local"),
        None,
    )
    assert local_repo is not None
    hook_ids = [h["id"] for h in local_repo.get("hooks", [])]
    assert "dev-stack-pipeline" in hook_ids
