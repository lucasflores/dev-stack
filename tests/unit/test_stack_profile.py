"""Tests for StackProfile dataclass and detect_stack_profile() function.

Covers:
- Pure markdown repo → has_python=False
- Repo with .py file → has_python=True
- .py only in .venv/ → has_python=False (excluded)
- .py only in __pycache__/ → has_python=False (excluded)
- Mixed repo → has_python=True
- Empty repo → has_python=False
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dev_stack.config import StackProfile, detect_stack_profile


def test_pure_markdown_repo(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Hello")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_repo_with_python_file(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is True


def test_python_only_in_venv_excluded(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "site.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_python_only_in_pycache_excluded(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "module.cpython-312.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_python_only_in_venv_dir_excluded(tmp_path: Path) -> None:
    (tmp_path / "venv" / "lib").mkdir(parents=True)
    (tmp_path / "venv" / "lib" / "site.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_python_only_in_node_modules_excluded(tmp_path: Path) -> None:
    (tmp_path / "node_modules" / "some-pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "some-pkg" / "script.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_python_only_in_dot_git_excluded(tmp_path: Path) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "hooks" / "pre-commit.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_python_only_in_dot_dev_stack_excluded(tmp_path: Path) -> None:
    (tmp_path / ".dev-stack").mkdir()
    (tmp_path / ".dev-stack" / "cache.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_mixed_repo_with_python(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Hello")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run.py").write_text("print('hello')")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is True


def test_empty_repo(tmp_path: Path) -> None:
    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is False


def test_script_in_root(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text("")

    profile = detect_stack_profile(tmp_path)

    assert profile.has_python is True


def test_stack_profile_is_frozen() -> None:
    profile = StackProfile(has_python=True)
    with pytest.raises(AttributeError):
        profile.has_python = False  # type: ignore[misc]
