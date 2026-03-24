"""Tests for stack-aware hook generation (US2).

Covers:
- _build_hook_list with has_python=False → only dev-stack-pipeline
- _build_hook_list with has_python=True → pipeline + ruff + pytest + mypy
- _render_pre_commit_config → YAML with managed section markers
- User hook preservation outside managed section
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.config import StackProfile
from dev_stack.modules.hooks import HookEntry, _build_hook_list, _render_pre_commit_config


def test_build_hook_list_no_python() -> None:
    """T011: has_python=False → only dev-stack-pipeline hook."""
    profile = StackProfile(has_python=False)

    hooks = _build_hook_list(profile)

    assert len(hooks) == 1
    assert hooks[0].id == "dev-stack-pipeline"


def test_build_hook_list_with_python() -> None:
    """T012: has_python=True → pipeline + ruff + pytest + mypy."""
    profile = StackProfile(has_python=True)

    hooks = _build_hook_list(profile)

    ids = [h.id for h in hooks]
    assert ids == ["dev-stack-pipeline", "dev-stack-ruff", "dev-stack-pytest", "dev-stack-mypy"]


def test_render_pre_commit_config_has_yaml_structure() -> None:
    """T013: Rendered YAML has proper repos/hooks structure."""
    profile = StackProfile(has_python=False)
    hooks = _build_hook_list(profile)

    yaml_str = _render_pre_commit_config(hooks)

    assert "repos:" in yaml_str
    assert "repo: local" in yaml_str
    assert "dev-stack-pipeline" in yaml_str


def test_managed_section_markers_applied(tmp_path: Path) -> None:
    """T013 extended: After write_managed_section, file contains markers."""
    from dev_stack.brownfield.markers import write_managed_section

    profile = StackProfile(has_python=False)
    hooks = _build_hook_list(profile)
    rendered = _render_pre_commit_config(hooks)

    config_path = tmp_path / ".pre-commit-config.yaml"
    write_managed_section(config_path, "HOOKS", rendered)

    content = config_path.read_text()
    assert "DEV-STACK:BEGIN:HOOKS" in content
    assert "DEV-STACK:END:HOOKS" in content


def test_user_hooks_preserved_outside_managed_section(tmp_path: Path) -> None:
    """T014: Existing hooks outside managed section survive re-init."""
    config_path = tmp_path / ".pre-commit-config.yaml"
    user_content = (
        "repos:\n"
        "  - repo: https://github.com/user/custom-hook\n"
        "    rev: v1.0\n"
        "    hooks:\n"
        "      - id: my-custom-hook\n"
    )
    config_path.write_text(user_content)

    from dev_stack.brownfield.markers import write_managed_section

    profile = StackProfile(has_python=False)
    hooks = _build_hook_list(profile)
    rendered = _render_pre_commit_config(hooks)

    # Simulate what install() does: write managed section
    write_managed_section(config_path, "HOOKS", rendered)

    result = config_path.read_text()
    assert "my-custom-hook" in result
    assert "dev-stack-pipeline" in result
    assert "DEV-STACK:BEGIN:HOOKS" in result
