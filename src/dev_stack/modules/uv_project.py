"""UV Project module — Python project scaffolding via uv."""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Sequence

import tomli_w

from .base import ModuleBase, ModuleResult, ModuleStatus

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """Convert a directory name to a valid Python identifier per PEP 503/625.

    1. Lowercase the entire string.
    2. Replace hyphens and dots with underscores.
    3. Strip any character that is not alphanumeric or underscore.
    4. Collapse consecutive underscores.
    5. Strip leading/trailing underscores.
    6. If the result starts with a digit, prepend an underscore.
    7. If the result is empty, fall back to ``"package"``.
    """
    result = name.lower()
    result = re.sub(r"[-.]", "_", result)
    result = re.sub(r"[^a-z0-9_]", "", result)
    result = re.sub(r"_+", "_", result)
    result = result.strip("_")
    if not result:
        return "package"
    if result[0].isdigit():
        result = f"_{result}"
    return result


# Directories excluded from root-level Python source scanning
_SCAN_EXCLUDE_DIRS = frozenset({".git", "__pycache__", ".venv", "node_modules", ".tox"})


def scan_root_python_sources(repo_root: Path) -> tuple[bool, list[str]]:
    """Scan the repo root at depth 1 for Python files and packages.

    Returns ``(has_python_sources, package_names)`` where *package_names*
    lists directories that contain ``__init__.py``.
    """
    has_py = False
    packages: list[str] = []
    try:
        entries = list(repo_root.iterdir())
    except OSError:
        return False, []
    for entry in entries:
        if entry.name in _SCAN_EXCLUDE_DIRS:
            continue
        if entry.is_file() and entry.suffix == ".py":
            has_py = True
        elif entry.is_dir() and (entry / "__init__.py").is_file():
            has_py = True
            packages.append(entry.name)
    return has_py, sorted(packages)


def _run_uv_init(repo_root: Path, pkg_name: str) -> tuple[bool, str]:
    """Shell out to ``uv init --package --name <name>``.

    Initializes the project in *repo_root* (no path argument to avoid the
    subdirectory trap).  Returns ``(success, output)`` tuple.
    """
    if not shutil.which("uv"):
        return False, "uv CLI not found on PATH"
    try:
        completed = subprocess.run(
            ("uv", "init", "--package", "--name", pkg_name),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "uv CLI not found on PATH"
    output_parts = [p.strip() for p in (completed.stdout, completed.stderr) if p.strip()]
    output = "\n".join(output_parts)
    return completed.returncode == 0, output


def _augment_pyproject(path: Path, pkg_name: str) -> list[str]:
    """Read ``pyproject.toml``, add opinionated tool sections (skip-if-exists), write back.

    Returns a list of section names that were added.
    """
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    added: list[str] = []
    tool = data.setdefault("tool", {})

    # --- [tool.ruff] ---
    if "ruff" not in tool:
        tool["ruff"] = {
            "target-version": "py311",
            "line-length": 88,
            "lint": {
                "select": ["E", "F", "I", "N", "W", "UP"],
                "ignore": [],
            },
        }
        added.append("tool.ruff")

    # --- [tool.pytest.ini_options] ---
    if "pytest" not in tool:
        tool["pytest"] = {
            "ini_options": {
                "testpaths": ["tests"],
                "addopts": "--strict-markers -v",
            },
        }
        added.append("tool.pytest.ini_options")

    # --- [tool.coverage.run] ---
    if "coverage" not in tool:
        tool["coverage"] = {
            "run": {
                "source": [f"src/{pkg_name}"],
                "omit": ["tests/*"],
            },
        }
        added.append("tool.coverage.run")

    # --- [tool.mypy] ---
    if "mypy" not in tool:
        # Read python version from .python-version if available
        python_version = "3.11"
        pv_path = path.parent / ".python-version"
        if pv_path.exists():
            raw = pv_path.read_text(encoding="utf-8").strip()
            parts = raw.split(".")
            if len(parts) >= 2:
                python_version = f"{parts[0]}.{parts[1]}"
        tool["mypy"] = {
            "python_version": python_version,
            "strict": False,
            "warn_return_any": True,
            "warn_unused_configs": True,
            "disallow_incomplete_defs": True,
            "check_untyped_defs": True,
            "mypy_path": "src",
        }
        added.append("tool.mypy")

    # --- [project.optional-dependencies] ---
    project = data.setdefault("project", {})
    opt_deps = project.setdefault("optional-dependencies", {})

    if "docs" not in opt_deps:
        opt_deps["docs"] = [
            "sphinx>=7.0",
            "sphinx-autodoc-typehints>=2.0",
            "myst-parser>=3.0",
        ]
        added.append("project.optional-dependencies.docs")

    if "dev" not in opt_deps:
        opt_deps["dev"] = [
            "mypy>=1.10",
            "pytest>=7.4",
            "pytest-cov>=4.1",
            "ruff>=0.3",
        ]
        added.append("project.optional-dependencies.dev")

    if added:
        with open(path, "wb") as fh:
            tomli_w.dump(data, fh)

    return added


def _scaffold_tests(repo_root: Path, pkg_name: str) -> list[Path]:
    """Create ``tests/__init__.py`` and ``tests/test_placeholder.py``.

    Returns a list of newly created paths.
    """
    tests_dir = repo_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []

    init_file = tests_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")
        created.append(init_file)

    placeholder = tests_dir / "test_placeholder.py"
    if not placeholder.exists():
        placeholder.write_text(
            f'"""Placeholder test generated by dev-stack."""\n\n\n'
            f"def test_import_{pkg_name}() -> None:\n"
            f"    import {pkg_name}  # noqa: F401\n",
            encoding="utf-8",
        )
        created.append(placeholder)

    return created


def _run_uv_lock(repo_root: Path) -> tuple[bool, str]:
    """Run ``uv lock`` in *repo_root*.  Returns ``(success, output)``."""
    if not shutil.which("uv"):
        return False, "uv CLI not found on PATH"
    try:
        completed = subprocess.run(
            ("uv", "lock"),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "uv CLI not found on PATH"
    output_parts = [p.strip() for p in (completed.stdout, completed.stderr) if p.strip()]
    output = "\n".join(output_parts)
    return completed.returncode == 0, output


_STANDARD_GITIGNORE_ENTRIES = [
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    ".venv/",
    ".codeboarding/cache/",
    ".codeboarding/logs/",
    "dist/",
    "*.egg-info/",
]


def _ensure_standard_gitignore(repo_root: Path) -> bool:
    """Append standard Python ignores to ``.gitignore`` if missing.

    Returns True if the file was modified.
    """
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
    else:
        content = ""

    missing = [entry for entry in _STANDARD_GITIGNORE_ENTRIES if entry not in content]
    if not missing:
        return False

    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n".join(missing) + "\n"
    gitignore.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Module class
# ---------------------------------------------------------------------------


class UvProjectModule(ModuleBase):
    """Scaffold a complete Python project via ``uv init --package``."""

    NAME = "uv_project"
    VERSION = "0.1.0"
    DEPENDS_ON: Sequence[str] = ()
    MANAGED_FILES: Sequence[str] = (
        "pyproject.toml",
        ".python-version",
        ".gitignore",
        "README.md",
        "uv.lock",
        "tests/__init__.py",
        "tests/test_placeholder.py",
        # src/{pkg}/__init__.py is dynamic — registered at install time
    )

    # ------------------------------------------------------------------
    # install (T010)
    # ------------------------------------------------------------------

    def install(self, *, force: bool = False) -> ModuleResult:
        pkg_name = _normalize_name(self.repo_root.resolve().name)
        created: list[Path] = []
        warnings: list[str] = []

        # --- uv check ---
        if not shutil.which("uv"):
            return ModuleResult(
                success=False,
                message="uv CLI not found — install uv (https://docs.astral.sh/uv/)",
            )

        pyproject = self.repo_root / "pyproject.toml"
        brownfield = pyproject.exists()

        # --- Brownfield guard ---
        if brownfield and not force:
            # Delegate conflict detection to preview_files flow
            return ModuleResult(
                success=False,
                message="pyproject.toml already exists — run with force=True or resolve conflicts",
            )

        # --- Step 1: uv init (greenfield only) ---
        if not brownfield:
            ok, output = _run_uv_init(self.repo_root, pkg_name)
            if not ok:
                # Clean up any partial artifacts
                for partial in ("pyproject.toml", ".python-version", ".gitignore", "README.md"):
                    p = self.repo_root / partial
                    if p.exists():
                        p.unlink()
                src_pkg = self.repo_root / "src" / pkg_name
                if src_pkg.exists():
                    shutil.rmtree(src_pkg)
                return ModuleResult(
                    success=False,
                    message=f"uv init failed: {output}",
                )
            # Record files created by uv init
            for rel in ("pyproject.toml", ".python-version", ".gitignore", "README.md"):
                p = self.repo_root / rel
                if p.exists():
                    created.append(p)
            src_init = self.repo_root / "src" / pkg_name / "__init__.py"
            if src_init.exists():
                created.append(src_init)

        # --- Step 2: augment pyproject.toml ---
        added_sections = _augment_pyproject(pyproject, pkg_name)
        if added_sections:
            warnings.append(f"Added TOML sections: {', '.join(added_sections)}")

        # --- Step 3: scaffold tests ---
        test_files = _scaffold_tests(self.repo_root, pkg_name)
        created.extend(test_files)

        # --- Step 4: uv lock ---
        lock_ok, lock_output = _run_uv_lock(self.repo_root)
        if lock_ok:
            lock_path = self.repo_root / "uv.lock"
            if lock_path.exists():
                created.append(lock_path)
        else:
            warnings.append(f"uv lock failed: {lock_output}")

        # --- Step 5: augment .gitignore with standard Python entries ---
        if _ensure_standard_gitignore(self.repo_root):
            gitignore_path = self.repo_root / ".gitignore"
            if gitignore_path not in created:
                created.append(gitignore_path)

        return ModuleResult(
            success=True,
            message=f"UV project initialized: {pkg_name}",
            files_created=created,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # verify (T011)
    # ------------------------------------------------------------------

    def verify(self) -> ModuleStatus:
        pkg_name = self._detect_package_name()
        missing: list[str] = []

        checks = {
            "pyproject.toml": self.repo_root / "pyproject.toml",
            ".python-version": self.repo_root / ".python-version",
            "uv.lock": self.repo_root / "uv.lock",
        }
        if pkg_name:
            checks[f"src/{pkg_name}/__init__.py"] = (
                self.repo_root / "src" / pkg_name / "__init__.py"
            )

        for label, path in checks.items():
            if not path.exists():
                missing.append(label)

        healthy = len(missing) == 0
        issue = f"Missing: {', '.join(missing)}" if missing else None
        return ModuleStatus(
            name=self.NAME,
            installed=True,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
        )

    # ------------------------------------------------------------------
    # uninstall + update (T012)
    # ------------------------------------------------------------------

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        # Remove only test scaffold and lockfile; leave pyproject.toml and src/
        for rel in ("tests/test_placeholder.py", "uv.lock"):
            p = self.repo_root / rel
            if p.exists():
                p.unlink()
                deleted.append(p)
        # Remove tests/__init__.py only if tests dir is now empty
        tests_init = self.repo_root / "tests" / "__init__.py"
        tests_dir = self.repo_root / "tests"
        if tests_init.exists():
            remaining = [f for f in tests_dir.iterdir() if f.name != "__init__.py"]
            if not remaining:
                tests_init.unlink()
                deleted.append(tests_init)
        return ModuleResult(True, "UV project artifacts removed", files_deleted=deleted)

    def update(self) -> ModuleResult:
        pkg_name = self._detect_package_name() or _normalize_name(self.repo_root.name)
        pyproject = self.repo_root / "pyproject.toml"
        warnings: list[str] = []

        if not pyproject.exists():
            return ModuleResult(
                success=False,
                message="pyproject.toml not found — nothing to update",
            )

        added_sections = _augment_pyproject(pyproject, pkg_name)
        if added_sections:
            warnings.append(f"Added TOML sections: {', '.join(added_sections)}")
            # Re-lock if pyproject.toml was modified
            lock_ok, lock_output = _run_uv_lock(self.repo_root)
            if not lock_ok:
                warnings.append(f"uv lock failed: {lock_output}")

        msg = "UV project updated" if added_sections else "UV project already up to date"
        return ModuleResult(
            success=True,
            message=msg,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # preview_files (for brownfield conflict detection)
    # ------------------------------------------------------------------

    def preview_files(self) -> dict[Path, str]:
        pkg_name = self._detect_package_name() or _normalize_name(self.repo_root.resolve().name)
        files: dict[Path, str] = {}

        # Generate the augmented pyproject.toml content
        pyproject = self.repo_root / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as fh:
                data = tomllib.load(fh)
        else:
            data = {}

        # Simulate augmentation on a copy
        import copy

        data_copy = copy.deepcopy(data)
        tool = data_copy.setdefault("tool", {})
        if "ruff" not in tool:
            tool["ruff"] = {
                "target-version": "py311",
                "line-length": 88,
                "lint": {"select": ["E", "F", "I", "N", "W", "UP"], "ignore": []},
            }
        if "pytest" not in tool:
            tool["pytest"] = {
                "ini_options": {"testpaths": ["tests"], "addopts": "--strict-markers -v"},
            }
        if "coverage" not in tool:
            tool["coverage"] = {
                "run": {"source": [f"src/{pkg_name}"], "omit": ["tests/*"]},
            }
        if "mypy" not in tool:
            tool["mypy"] = {
                "python_version": "3.11",
                "strict": False,
                "warn_return_any": True,
                "warn_unused_configs": True,
                "disallow_incomplete_defs": True,
                "check_untyped_defs": True,
                "mypy_path": "src",
            }
        project = data_copy.setdefault("project", {})
        opt_deps = project.setdefault("optional-dependencies", {})
        if "docs" not in opt_deps:
            opt_deps["docs"] = ["sphinx>=7.0", "sphinx-autodoc-typehints>=2.0", "myst-parser>=3.0"]
        if "dev" not in opt_deps:
            opt_deps["dev"] = ["mypy>=1.10", "pytest>=7.4", "pytest-cov>=4.1", "ruff>=0.3"]

        import io

        buf = io.BytesIO()
        tomli_w.dump(data_copy, buf)
        files[Path("pyproject.toml")] = buf.getvalue().decode("utf-8")

        files[Path(f"src/{pkg_name}/__init__.py")] = f'"""Top-level package for {pkg_name}."""\n'
        files[Path("tests/__init__.py")] = ""
        files[Path("tests/test_placeholder.py")] = (
            f'"""Placeholder test generated by dev-stack."""\n\n\n'
            f"def test_import_{pkg_name}() -> None:\n"
            f"    import {pkg_name}  # noqa: F401\n"
        )
        return files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_package_name(self) -> str | None:
        """Resolve package name from manifest or ``src/`` directory scan."""
        # Try manifest first
        modules = self.manifest.get("modules", {})
        uv_entry = modules.get("uv_project", {})
        config = uv_entry.get("config", {})
        if "package_name" in config:
            return config["package_name"]
        # Fall back to scanning src/
        src_dir = self.repo_root / "src"
        if src_dir.is_dir():
            candidates = sorted(
                d.name for d in src_dir.iterdir() if d.is_dir() and (d / "__init__.py").is_file()
            )
            if candidates:
                return candidates[0]
        return None


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(UvProjectModule)
