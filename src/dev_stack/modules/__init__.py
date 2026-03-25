"""Module registry and resolver utilities."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Type

from ..errors import DependencyError
from ..manifest import DEFAULT_MODULE_VERSION, ModuleEntry, StackManifest
from .base import ModuleBase

ModuleClass = Type[ModuleBase]

_MODULE_REGISTRY: Dict[str, ModuleClass] = {}
DEFAULT_GREENFIELD_MODULES: Sequence[str] = ("uv_project", "sphinx_docs", "hooks", "apm", "vcs_hooks")

DEPRECATED_MODULES: dict[str, str] = {
	"speckit": (
		"The 'speckit' module has been removed. "
		"Agent dependencies are now managed by the 'apm' module. "
		"Run 'specify init --here --ai copilot' to set up the .specify/ directory."
	),
}


def register_module(cls: ModuleClass) -> ModuleClass:
	"""Register a module class for resolver lookups."""

	_MODULE_REGISTRY[cls.NAME] = cls
	return cls


def available_modules() -> tuple[str, ...]:
	return tuple(sorted(_MODULE_REGISTRY.keys()))


def resolve_module_names(
	requested: Iterable[str] | None = None,
	*,
	include_defaults: bool = True,
) -> list[str]:
	"""Resolve modules plus dependencies in deterministic order."""

	requested_set = OrderedDict()
	if include_defaults:
		for name in DEFAULT_GREENFIELD_MODULES:
			requested_set.setdefault(name, None)
	if requested:
		for name in requested:
			requested_set.setdefault(name, None)

	resolved: list[str] = []
	seen: set[str] = set()
	visiting: set[str] = set()

	def visit(name: str) -> None:
		if name in seen:
			return
		if name in visiting:
			raise DependencyError(name, ["cyclical dependency"])
		module_cls = _MODULE_REGISTRY.get(name)
		if module_cls is None:
			raise KeyError(f"Unknown module '{name}'")
		visiting.add(name)
		for dep in module_cls.DEPENDS_ON:
			visit(dep)
		visiting.remove(name)
		seen.add(name)
		resolved.append(name)

	for candidate in requested_set.keys():
		visit(candidate)

	return resolved


def instantiate_modules(
	repo_root: Path,
	manifest: StackManifest | None,
	module_names: Sequence[str],
) -> list[ModuleBase]:
	"""Instantiate modules in resolved order."""

	instances: list[ModuleBase] = []
	for name in module_names:
		module_cls = _MODULE_REGISTRY[name]
		instances.append(module_cls(repo_root, manifest.to_dict() if manifest else None))
	return instances


def latest_module_entries(module_names: Sequence[str] | None = None) -> dict[str, ModuleEntry]:
	"""Return canonical module metadata for the requested names."""

	names = list(module_names) if module_names else list(_MODULE_REGISTRY.keys())
	snapshot: dict[str, ModuleEntry] = {}
	for name in names:
		module_cls = _MODULE_REGISTRY.get(name)
		if module_cls is None:
			continue
		version = getattr(module_cls, "VERSION", DEFAULT_MODULE_VERSION)
		snapshot[name] = ModuleEntry(version=version, installed=True)
	return snapshot


# Import built-in modules so they register themselves.
from . import apm, ci_workflows, docker, hooks, mcp_servers, sphinx_docs, uv_project, vcs_hooks, visualization  # noqa: E402,F401
