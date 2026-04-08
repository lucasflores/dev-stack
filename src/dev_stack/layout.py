"""Package layout detection for Python projects.

Provides a shared ``detect_package_layout()`` utility that discovers the
project's package root across ``src``, flat, and namespace layouts.  The
detection follows a strict precedence:

1. Explicit manifest config (``modules.uv_project.config.package_name``).
2. ``pyproject.toml`` build-backend hints (setuptools, hatch).
3. ``src/`` directory scan.
4. Repo-root scan.
5. Default SRC layout with empty package_names (greenfield).
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class LayoutStyle(Enum):
    """Classification of how a Python project organizes its packages."""

    SRC = "src"
    FLAT = "flat"
    NAMESPACE = "namespace"


@dataclass(frozen=True, slots=True)
class PackageLayout:
    """Immutable result of package layout detection.

    *package_root* is always relative to the repository root.
    *package_names* is always sorted alphabetically.
    """

    layout_style: LayoutStyle
    package_root: Path
    package_names: list[str]

    def __post_init__(self) -> None:
        if self.package_root.is_absolute():
            raise ValueError("package_root must be a relative path")
        # Ensure package_names is sorted (frozen=True so we sort in-place on the list)
        object.__setattr__(self, "package_names", sorted(self.package_names))


# ---------------------------------------------------------------------------
# Scanning helpers (relocated from modules/uv_project.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Detection – precedence levels
# ---------------------------------------------------------------------------


def _check_manifest_config(
    repo_root: Path, manifest: dict[str, Any]
) -> PackageLayout | None:
    """Precedence level 1: explicit manifest config."""
    modules = manifest.get("modules", {})
    uv_entry = modules.get("uv_project", {})
    config = uv_entry.get("config", {})
    name: str | None = config.get("package_name")
    if not name:
        return None

    # Resolve layout style from filesystem
    if (repo_root / "src" / name).is_dir():
        return PackageLayout(LayoutStyle.SRC, Path("src"), [name])
    if (repo_root / name).is_dir():
        return PackageLayout(LayoutStyle.FLAT, Path("."), [name])
    # Default to SRC when the directory doesn't exist yet
    return PackageLayout(LayoutStyle.SRC, Path("src"), [name])


def _check_setuptools_hints(
    repo_root: Path, pyproject: dict[str, Any]
) -> PackageLayout | None:
    """Precedence level 2a: setuptools ``[tool.setuptools.packages.find]``."""
    find_cfg = (
        pyproject.get("tool", {})
        .get("setuptools", {})
        .get("packages", {})
        .get("find", {})
    )
    if not find_cfg:
        return None

    where: list[str] = find_cfg.get("where", ["."])
    root_str = where[0] if where else "."
    root_path = Path(root_str)

    is_namespace: bool = find_cfg.get("namespaces", False)
    style = LayoutStyle.NAMESPACE if is_namespace else (
        LayoutStyle.SRC if root_str == "src" else LayoutStyle.FLAT
    )

    # Scan the designated root for packages
    scan_dir = repo_root / root_path
    if scan_dir.is_dir():
        pkgs = sorted(
            d.name
            for d in scan_dir.iterdir()
            if d.is_dir() and (d / "__init__.py").is_file()
        )
    else:
        logger.warning(
            "setuptools packages.find.where=%r does not exist; falling through",
            root_str,
        )
        return None

    pkg_root = Path(".") if root_str == "." else root_path
    return PackageLayout(style, pkg_root, pkgs)


def _check_hatch_hints(
    repo_root: Path, pyproject: dict[str, Any]
) -> PackageLayout | None:
    """Precedence level 2b: hatch ``[tool.hatch.build.targets.wheel]``."""
    wheel_cfg = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
    )
    packages: list[str] = wheel_cfg.get("packages", [])
    if not packages:
        return None

    # Derive package root and names from the first entry's parent
    first = Path(packages[0])
    root = first.parent if first.parent != Path(".") else Path(".")
    names: list[str] = []
    for p in packages:
        pp = Path(p)
        pkg_dir = repo_root / pp
        if pkg_dir.is_dir():
            names.append(pp.name)
        else:
            logger.warning(
                "hatch packages entry %r does not exist; skipping", p,
            )

    if not names:
        return None

    style = LayoutStyle.SRC if str(root) == "src" else LayoutStyle.FLAT
    pkg_root = Path(".") if root == Path(".") else root
    return PackageLayout(style, pkg_root, names)


def _check_pyproject_hints(
    repo_root: Path,
) -> PackageLayout | None:
    """Precedence level 2: read ``pyproject.toml`` and check build-backend hints."""
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        return None
    try:
        with open(pyproject_path, "rb") as fh:
            pyproject = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        logger.warning("Could not parse pyproject.toml; skipping hint detection")
        return None

    # 2a: setuptools
    result = _check_setuptools_hints(repo_root, pyproject)
    if result is not None:
        return result

    # 2b: hatch
    result = _check_hatch_hints(repo_root, pyproject)
    if result is not None:
        return result

    return None


def _check_src_directory(repo_root: Path) -> PackageLayout | None:
    """Precedence level 3: scan ``repo_root/src/`` for packages."""
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return None
    candidates = sorted(
        d.name
        for d in src_dir.iterdir()
        if d.is_dir() and (d / "__init__.py").is_file()
    )
    if not candidates:
        return None
    return PackageLayout(LayoutStyle.SRC, Path("src"), candidates)


def _check_repo_root(repo_root: Path) -> PackageLayout | None:
    """Precedence level 4: scan repo root for flat-layout packages."""
    _has_py, packages = scan_root_python_sources(repo_root)
    if packages:
        return PackageLayout(LayoutStyle.FLAT, Path("."), packages)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_package_layout(
    repo_root: Path,
    manifest: dict[str, Any] | None = None,
) -> PackageLayout:
    """Detect the Python package layout for a repository.

    Follows a strict precedence order (see module docstring).  Never raises
    and never returns ``None`` — falls back to a default SRC layout with
    empty *package_names* when nothing is found.
    """
    # Level 1: explicit manifest config
    if manifest is not None:
        result = _check_manifest_config(repo_root, manifest)
        if result is not None:
            return result

    # Level 2: pyproject.toml build-backend hints
    result = _check_pyproject_hints(repo_root)
    if result is not None:
        return result

    # Level 3: src/ directory scan
    result = _check_src_directory(repo_root)
    if result is not None:
        # FR-014: warn if flat packages also exist
        _has_py, root_pkgs = scan_root_python_sources(repo_root)
        if root_pkgs:
            logger.warning(
                "Found packages in both src/ and repo root: src/=%s root=%s; "
                "using src/ layout",
                result.package_names,
                root_pkgs,
            )
        return result

    # Level 4: repo-root scan
    result = _check_repo_root(repo_root)
    if result is not None:
        return result

    # Level 5: default SRC (greenfield)
    return PackageLayout(LayoutStyle.SRC, Path("src"), [])
