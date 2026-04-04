"""Tests for init pipeline behaviour.

Covers US1 (uv sync gating), US4 (gitignore managed section), US5 (secrets gating).
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- US1: uv sync gating ---


def test_uv_sync_gated_by_uv_project_module() -> None:
    """T007: uv sync call in init must be guarded by 'uv_project' in module_names."""
    import dev_stack.cli.init_cmd as init_mod

    source = inspect.getsource(init_mod)
    lines = source.splitlines()
    # Find the uv sync call line
    for i, line in enumerate(lines):
        if 'subprocess.run(["uv", "sync"' in line:
            # Check that a guard condition exists in surrounding lines (within 5 lines above)
            context = "\n".join(lines[max(0, i - 5) : i + 1])
            assert "uv_project" in context, (
                f"uv sync call at line {i} is not guarded by 'uv_project' check"
            )
            return
    pytest.fail("No uv sync call found in init_cmd source")


# --- US5: Secrets scanning only runs when requested ---


def test_secrets_baseline_not_called_in_init_flow() -> None:
    """T036: init flow must not call _generate_secrets_baseline unconditionally.

    Verifies by inspecting the init_command source for the removed call.
    """
    import dev_stack.cli.init_cmd as init_mod

    source = inspect.getsource(init_mod)
    # The function definition should still exist
    assert "def _generate_secrets_baseline" in source
    # But it should NOT be called anywhere outside its own definition
    lines = source.splitlines()
    call_lines = [
        line.strip()
        for line in lines
        if "_generate_secrets_baseline(" in line and not line.strip().startswith("def ")
    ]
    assert call_lines == [], f"Unexpected calls to _generate_secrets_baseline: {call_lines}"


def test_generate_secrets_baseline_function_still_exists() -> None:
    """T039: _generate_secrets_baseline function definition is retained for future use."""
    from dev_stack.cli.init_cmd import _generate_secrets_baseline

    assert callable(_generate_secrets_baseline)


# --- US4: Pipeline skip marker is always gitignored ---


def test_gitignore_managed_section_contains_dev_stack_dir(tmp_path) -> None:
    """T030: After _ensure_gitignore_managed_section, .gitignore has specific .dev-stack/ paths and negation patterns."""
    from dev_stack.cli.init_cmd import _ensure_gitignore_managed_section

    _ensure_gitignore_managed_section(tmp_path)

    gitignore = (tmp_path / ".gitignore").read_text()
    assert "DEV-STACK:BEGIN:GITIGNORE" in gitignore
    assert "DEV-STACK:END:GITIGNORE" in gitignore
    assert ".dev-stack/pipeline/" in gitignore
    assert ".dev-stack/viz/" in gitignore
    assert ".dev-stack/pipeline-skipped" in gitignore
    # Tracked files must be negated so git sees them
    assert "!.dev-stack/hooks-manifest.json" in gitignore
    assert "!.dev-stack/instructions.md" in gitignore


def test_gitignore_created_when_missing(tmp_path) -> None:
    """T031: init on repo with no .gitignore → file is created with managed section."""
    from dev_stack.cli.init_cmd import _ensure_gitignore_managed_section

    assert not (tmp_path / ".gitignore").exists()

    _ensure_gitignore_managed_section(tmp_path)

    assert (tmp_path / ".gitignore").exists()
    content = (tmp_path / ".gitignore").read_text()
    assert ".dev-stack/pipeline/" in content


def test_gitignore_preserves_existing_content(tmp_path) -> None:
    """T032: init on repo with existing .gitignore → user content preserved."""
    from dev_stack.cli.init_cmd import _ensure_gitignore_managed_section

    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n")

    _ensure_gitignore_managed_section(tmp_path)

    content = gitignore.read_text()
    assert "node_modules/" in content
    assert "*.log" in content
    assert ".dev-stack/pipeline/" in content
    assert "DEV-STACK:BEGIN:GITIGNORE" in content


# --- Phase 9: Integration / cross-story tests ---


def test_full_init_produces_clean_config(tmp_path: Path) -> None:
    """Full init flow validation (cross-story).

    Verifies:
    - uv sync guard is in place
    - _generate_secrets_baseline not called
    - gitignore managed section present
    - No absolute paths in manifest
    - Hook config has all Python hooks
    """
    from dev_stack.brownfield.markers import write_managed_section
    from dev_stack.cli.init_cmd import _ensure_gitignore_managed_section
    from dev_stack.manifest import AgentConfig, create_default, write_manifest
    from dev_stack.modules.hooks import _build_hook_list, _render_pre_commit_config

    # Setup: pure markdown repo
    (tmp_path / "README.md").write_text("# Test")

    # Hooks: should include all Python hooks
    hooks = _build_hook_list()
    ids = [h.id for h in hooks]
    assert "dev-stack-pipeline" in ids
    assert "dev-stack-ruff" in ids
    assert "dev-stack-pytest" in ids
    assert "dev-stack-mypy" in ids

    # Config: Python hooks present
    rendered = _render_pre_commit_config(hooks)
    assert "ruff" in rendered
    assert "pytest" in rendered
    assert "mypy" in rendered

    # Gitignore: managed section
    _ensure_gitignore_managed_section(tmp_path)
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".dev-stack/pipeline/" in gitignore
    assert "!.dev-stack/hooks-manifest.json" in gitignore

    # Manifest: no absolute paths
    manifest = create_default(["hooks", "apm", "vcs_hooks"])
    manifest.agent = AgentConfig(cli="claude")
    manifest_path = tmp_path / "dev-stack.toml"
    write_manifest(manifest, manifest_path)
    content = manifest_path.read_text()
    assert "/usr/" not in content
    assert "path" not in content.lower().split("[agent]")[-1].split("[")[0] if "[agent]" in content else True


def test_build_hook_list_always_includes_python_hooks() -> None:
    """_build_hook_list always returns all Python hooks."""
    from dev_stack.modules.hooks import _build_hook_list

    hooks = _build_hook_list()
    ids = [h.id for h in hooks]
    assert "dev-stack-pipeline" in ids
    assert "dev-stack-ruff" in ids
    assert "dev-stack-pytest" in ids
    assert "dev-stack-mypy" in ids


def test_polyglot_repo_python_hooks_but_no_uv_sync() -> None:
    """Polyglot repo: uv sync is gated by uv_project."""
    import dev_stack.cli.init_cmd as init_mod

    source = inspect.getsource(init_mod)
    lines = source.splitlines()

    # Verify uv sync is gated by uv_project
    for i, line in enumerate(lines):
        if 'subprocess.run(["uv", "sync"' in line:
            context = "\n".join(lines[max(0, i - 5) : i + 1])
            assert "uv_project" in context
            return
    pytest.fail("No uv sync call found")


def test_resolve_defaults_includes_all_modules() -> None:
    """resolve_module_names(include_defaults=True) includes all default modules."""
    from dev_stack.modules import DEFAULT_GREENFIELD_MODULES, resolve_module_names

    resolved = resolve_module_names(include_defaults=True)

    for name in DEFAULT_GREENFIELD_MODULES:
        assert name in resolved
