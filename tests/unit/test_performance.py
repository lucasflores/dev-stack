"""Performance benchmarks — SC-006, SC-008, SC-010."""
from __future__ import annotations

import time
from pathlib import Path

import pytest


class TestPerformanceSC006:
    """SC-006: Hook operations complete in under 2 seconds."""

    def test_install_under_2s(self, tmp_path: Path) -> None:
        """VcsHooksModule.install() completes within 2s budget."""
        # Set up minimal repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hooks").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "bench"\nversion = "0.1.0"\n'
        )
        (tmp_path / ".dev-stack").mkdir()

        from dev_stack.modules.vcs_hooks import VcsHooksModule

        module = VcsHooksModule(repo_root=tmp_path)
        start = time.perf_counter()
        result = module.install()
        elapsed = time.perf_counter() - start

        assert result.success
        assert elapsed < 2.0, f"install() took {elapsed:.2f}s (budget: 2.0s)"

    def test_verify_under_2s(self, tmp_path: Path) -> None:
        """VcsHooksModule.verify() completes within 2s budget."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hooks").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "bench"\nversion = "0.1.0"\n'
        )
        (tmp_path / ".dev-stack").mkdir()

        from dev_stack.modules.vcs_hooks import VcsHooksModule

        module = VcsHooksModule(repo_root=tmp_path)
        module.install()

        start = time.perf_counter()
        status = module.verify()
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"verify() took {elapsed:.2f}s (budget: 2.0s)"


class TestPerformanceSC008:
    """SC-008: Constitution generation completes in under 1 second."""

    def test_constitutional_gen_under_1s(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hooks").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "bench"\nversion = "0.1.0"\n'
        )
        (tmp_path / ".dev-stack").mkdir()

        from dev_stack.modules.vcs_hooks import VcsHooksModule

        module = VcsHooksModule(repo_root=tmp_path)

        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []

        start = time.perf_counter()
        module._generate_constitutional_files(created, modified, warnings)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"_generate_constitutional_files() took {elapsed:.2f}s (budget: 1.0s)"


class TestPerformanceSC010:
    """SC-010: Scope advisory check completes in under 500ms."""

    def test_scope_check_under_500ms(self) -> None:
        from dev_stack.vcs.scope import check_scope

        # Generate a large realistic file list
        files = []
        for pkg in ("cli", "modules", "pipeline", "vcs", "rules", "brownfield"):
            for i in range(50):
                files.append(f"src/dev_stack/{pkg}/file_{i}.py")
        for i in range(50):
            files.append(f"tests/unit/test_{i}.py")
        for i in range(20):
            files.append(f"specs/00{i}/spec.md")

        start = time.perf_counter()
        result = check_scope(files)
        elapsed = time.perf_counter() - start

        assert result.triggered  # All rules should fire
        assert elapsed < 0.5, f"check_scope() took {elapsed:.3f}s (budget: 0.5s)"

    def test_scope_check_empty_fast(self) -> None:
        from dev_stack.vcs.scope import check_scope

        start = time.perf_counter()
        for _ in range(1000):
            check_scope([])
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"1000 empty check_scope() took {elapsed:.3f}s"
