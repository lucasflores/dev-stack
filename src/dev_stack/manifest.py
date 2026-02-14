"""Stack manifest reader and writer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import tomllib
import tomli_w

from .errors import ManifestError

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_STACK_VERSION = "0.1.0"
DEFAULT_MODULE_VERSION = "0.1.0"
DEFAULT_MODULES = ("hooks", "speckit")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        raise ManifestError("Datetime value missing")
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.rstrip("Z")) .replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ManifestError(f"Invalid datetime: {value}") from exc


@dataclass
class AgentConfig:
    cli: str = "none"
    path: str | None = None
    detected_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "cli": self.cli,
            "detected_at": self.detected_at.astimezone(timezone.utc).strftime(ISO_FORMAT),
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentConfig":
        detected = data.get("detected_at")
        detected_dt = _parse_datetime(detected) if detected else _now_utc()
        return cls(cli=data.get("cli", "none"), path=data.get("path"), detected_at=detected_dt)


@dataclass
class ModuleEntry:
    version: str = DEFAULT_MODULE_VERSION
    installed: bool = True
    depends_on: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "version": self.version,
            "installed": self.installed,
        }
        if self.depends_on:
            data["depends_on"] = list(self.depends_on)
        if self.config:
            data["config"] = self.config
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModuleEntry":
        return cls(
            version=data.get("version", DEFAULT_MODULE_VERSION),
            installed=bool(data.get("installed", True)),
            depends_on=list(data.get("depends_on", [])),
            config=dict(data.get("config", {})),
        )


@dataclass
class StackManifest:
    version: str
    initialized: datetime
    last_updated: datetime
    rollback_ref: str | None
    modules: dict[str, ModuleEntry] = field(default_factory=dict)
    agent: AgentConfig = field(default_factory=AgentConfig)
    mode: str = "unknown"

    def diff_modules(
        self,
        latest: Mapping[str, ModuleEntry],
        selection: Sequence[str] | None = None,
    ) -> "ModuleDelta":
        ordered_targets: list[str]
        if selection:
            ordered_targets = list(dict.fromkeys(selection))
        else:
            ordered_targets = list(self.modules.keys())
        if not ordered_targets and latest:
            ordered_targets = list(latest.keys())

        delta = ModuleDelta()
        for name in ordered_targets:
            latest_entry = latest.get(name)
            current_entry = self.modules.get(name)
            if latest_entry is None:
                if current_entry is not None:
                    delta.removed.append(name)
                else:
                    delta.removed.append(name)
                continue
            if current_entry is None or not current_entry.installed:
                delta.added.append(name)
            elif current_entry.version != latest_entry.version:
                delta.updated.append(name)
            else:
                delta.unchanged.append(name)
        return delta

    def to_dict(self) -> dict[str, Any]:
        stack_section = {
            "version": self.version,
            "initialized": self.initialized.astimezone(timezone.utc).strftime(ISO_FORMAT),
            "last_updated": self.last_updated.astimezone(timezone.utc).strftime(ISO_FORMAT),
        }
        if self.rollback_ref:
            stack_section["rollback_ref"] = self.rollback_ref
        stack_section["mode"] = self.mode
        modules_section = {name: module.to_dict() for name, module in self.modules.items()}
        return {
            "stack": stack_section,
            "agent": self.agent.to_dict(),
            "modules": modules_section,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StackManifest":
        stack_data = data.get("stack")
        if not stack_data:
            raise ManifestError("Missing [stack] section")
        initialized = _parse_datetime(stack_data.get("initialized"))
        last_updated = _parse_datetime(stack_data.get("last_updated"))
        modules_data = data.get("modules", {})
        modules = {name: ModuleEntry.from_dict(entry) for name, entry in modules_data.items()}
        if not modules:
            raise ManifestError("Manifest has no modules configured")
        agent = AgentConfig.from_dict(data.get("agent", {}))
        return cls(
            version=stack_data.get("version", DEFAULT_STACK_VERSION),
            initialized=initialized,
            last_updated=last_updated,
            rollback_ref=stack_data.get("rollback_ref"),
            modules=modules,
            agent=agent,
            mode=stack_data.get("mode", "unknown"),
        )


def create_default(modules: Iterable[str] | None = None) -> StackManifest:
    module_names = list(modules or DEFAULT_MODULES)
    timestamp = _now_utc()
    module_entries = {name: ModuleEntry() for name in module_names}
    return StackManifest(
        version=DEFAULT_STACK_VERSION,
        initialized=timestamp,
        last_updated=timestamp,
        rollback_ref=None,
        modules=module_entries,
        agent=AgentConfig(),
        mode="unknown",
    )


def read_manifest(path: str | Path) -> StackManifest:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise ManifestError(f"Manifest not found at {manifest_path}")
    with manifest_path.open("rb") as fh:
        data = tomllib.load(fh)
    return StackManifest.from_dict(data)


def write_manifest(manifest: StackManifest, path: str | Path) -> Path:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest.to_dict()
    with manifest_path.open("wb") as fh:
        tomli_w.dump(data, fh)
    return manifest_path


@dataclass(slots=True)
class ModuleDelta:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
