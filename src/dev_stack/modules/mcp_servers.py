"""MCP servers module implementation."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..config import AgentInfo, detect_agent, validate_env_vars
from ..errors import AgentUnavailableError, ConfigError
from ..manifest import StackManifest
from .base import ModuleBase, ModuleResult, ModuleStatus

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "mcp"
MANIFEST_PATH = TEMPLATE_DIR / "manifest.json"
PLACEHOLDER = "{{ SERVERS }}"
SUPPORTED_AGENTS = ("claude", "copilot")


@dataclass(slots=True)
class _ServerDefinition:
    name: str
    package: str
    command: list[str]
    health_check: list[str] | None
    env: list[str]
    description: str

    def to_config_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "package": self.package,
            "command": list(self.command),
            "env": list(self.env),
            "description": self.description,
        }

    def env_vars(self) -> Iterable[str]:
        return list(self.env)


class MCPServersModule(ModuleBase):
    NAME = "mcp-servers"
    VERSION = "0.1.0"
    MANAGED_FILES = (".claude/settings.local.json", ".github/copilot-mcp.json")

    def __init__(self, repo_root: Path, manifest: dict[str, Any] | None = None) -> None:
        super().__init__(repo_root, manifest)
        self._stack_manifest = StackManifest.from_dict(manifest) if manifest else None
        self._manifest_data = self._load_template_manifest()
        self._server_lookup = {
            entry["name"]: entry for entry in self._manifest_data.get("servers", [])
        }

    # ------------------------------------------------------------------
    def install(self, *, force: bool = False) -> ModuleResult:
        result, _, _ = self.install_selected(None, force=force)
        return result

    def install_selected(
        self,
        server_names: Sequence[str] | None,
        *,
        force: bool = False,
    ) -> tuple[ModuleResult, str, list[_ServerDefinition]]:
        agent = self._require_supported_agent()
        metadata = self._agent_metadata(agent.cli)
        server_defs = self._resolve_servers(server_names)
        created, modified, warnings = self._write_agent_config(metadata, server_defs, force=force)
        warnings.extend(self._missing_env_warnings(server_defs))
        message = f"Configured MCP servers for {agent.cli}"
        return ModuleResult(True, message, created, modified, warnings=warnings), agent.cli, server_defs

    def uninstall(self) -> ModuleResult:
        deleted: list[Path] = []
        for rel_path in self.MANAGED_FILES:
            target = self.repo_root / rel_path
            if target.exists():
                target.unlink()
                deleted.append(target)
        return ModuleResult(True, "Removed MCP server configs", files_deleted=deleted)

    def update(self) -> ModuleResult:
        return self.install(force=True)

    def verify(self) -> ModuleStatus:
        agent = detect_agent(self._stack_manifest)
        metadata = self._agent_metadata(agent.cli)
        if metadata is None:
            return ModuleStatus(
                name=self.NAME,
                installed=False,
                version=self.VERSION,
                healthy=False,
                issue="No supported coding agent detected",
                config={"agent": agent.cli},
            )
        target = self.repo_root / metadata["config_path"]
        installed = target.exists()
        server_defs = self._resolve_servers(None)
        env_status = self._env_status(server_defs)
        healthy = installed and all(env_status.values())
        issue = None
        if not installed:
            issue = f"{metadata['config_path']} missing"
        elif not healthy:
            missing = [name for name, ok in env_status.items() if not ok]
            issue = f"Missing env vars: {', '.join(missing)}"
        return ModuleStatus(
            name=self.NAME,
            installed=installed,
            version=self.VERSION,
            healthy=healthy,
            issue=issue,
            config={
                "agent": agent.cli,
                "env": env_status,
                "servers": [definition.name for definition in server_defs],
            },
        )

    def preview_files(self) -> dict[Path, str]:
        preview: dict[Path, str] = {}
        server_defs = self._resolve_servers(None)
        servers_payload = json.dumps([definition.to_config_entry() for definition in server_defs], indent=2)
        for agent_name in SUPPORTED_AGENTS:
            metadata = self._agent_metadata(agent_name)
            if not metadata:
                continue
            template = self._load_template(metadata["template"])
            rendered = template.replace(PLACEHOLDER, servers_payload)
            preview[Path(metadata["config_path"])] = rendered
        return preview

    # ------------------------------------------------------------------
    def get_server_definitions(self, server_names: Sequence[str] | None = None) -> list[_ServerDefinition]:
        return self._resolve_servers(server_names)

    def env_report(self, server_defs: Sequence[_ServerDefinition]) -> dict[str, bool]:
        return self._env_status(server_defs)

    def resolve_agent(self, require_supported: bool = True) -> AgentInfo:
        if require_supported:
            return self._require_supported_agent()
        return detect_agent(self._stack_manifest)

    def agent_output_path(self, agent_cli: str) -> Path | None:
        metadata = self._agent_metadata(agent_cli)
        if not metadata:
            return None
        return self.repo_root / metadata["config_path"]

    def run_health_check(self, server: _ServerDefinition) -> tuple[str, str]:
        if not server.health_check:
            return "skipped", "Health check not defined"
        command = server.health_check
        binary = command[0]
        if shutil.which(binary) is None:
            return "skipped", f"{binary} not available"
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=self.repo_root,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess failure surface
            return "fail", f"Exited with code {exc.returncode}"
        return "pass", "Healthy"

    # ------------------------------------------------------------------
    def _resolve_servers(self, names: Sequence[str] | None) -> list[_ServerDefinition]:
        selection: list[str]
        if names:
            selection = list(dict.fromkeys(names))
        else:
            selection = list(self._manifest_data.get("default_servers", []))
        missing = [name for name in selection if name not in self._server_lookup]
        if missing:
            raise ConfigError(f"Unknown MCP server(s): {', '.join(sorted(missing))}")
        definitions: list[_ServerDefinition] = []
        for name in selection:
            entry = self._server_lookup[name]
            definitions.append(
                _ServerDefinition(
                    name=name,
                    package=entry.get("package", name),
                    command=list(entry.get("command", [])),
                    health_check=list(entry["health_check"]) if entry.get("health_check") else None,
                    env=list(entry.get("env", [])),
                    description=entry.get("description", ""),
                )
            )
        return definitions

    def _require_supported_agent(self) -> AgentInfo:
        agent = detect_agent(self._stack_manifest)
        if agent.cli not in SUPPORTED_AGENTS or not agent.path:
            raise AgentUnavailableError("mcp")
        return agent

    def _agent_metadata(self, agent_cli: str | None) -> dict[str, str] | None:
        if not agent_cli:
            return None
        return self._manifest_data.get("agents", {}).get(agent_cli)

    def _write_agent_config(
        self,
        metadata: dict[str, str],
        server_defs: Sequence[_ServerDefinition],
        *,
        force: bool,
    ) -> tuple[list[Path], list[Path], list[str]]:
        created: list[Path] = []
        modified: list[Path] = []
        warnings: list[str] = []
        template = self._load_template(metadata["template"])
        payload = json.dumps([definition.to_config_entry() for definition in server_defs], indent=2)
        rendered = template.replace(PLACEHOLDER, payload)
        destination = self.repo_root / metadata["config_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        existed = destination.exists()
        if existed and not force:
            current = destination.read_text(encoding="utf-8")
            if current == rendered:
                return created, modified, warnings
            warnings.append(
                f"{metadata['config_path']} exists; re-run with --force to overwrite user changes."
            )
            return created, modified, warnings
        destination.write_text(rendered, encoding="utf-8")
        destination.chmod(0o644)
        if existed:
            modified.append(destination)
        else:
            created.append(destination)
        return created, modified, warnings

    def _load_template(self, relative_path: str) -> str:
        template_path = TEMPLATE_DIR / relative_path
        return template_path.read_text(encoding="utf-8")

    def _load_template_manifest(self) -> dict[str, Any]:
        if not MANIFEST_PATH.exists():
            raise ConfigError("MCP manifest template missing")
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return data

    def _env_status(self, server_defs: Sequence[_ServerDefinition]) -> dict[str, bool]:
        env_names: list[str] = []
        for server in server_defs:
            env_names.extend(server.env)
        if not env_names:
            return {}
        unique = list(dict.fromkeys(env_names))
        return validate_env_vars(unique)

    def _missing_env_warnings(self, server_defs: Sequence[_ServerDefinition]) -> list[str]:
        env_status = self._env_status(server_defs)
        missing = [name for name, present in env_status.items() if not present]
        if not missing:
            return []
        return [f"Missing environment variables: {', '.join(missing)}"]


def register(module_cls: type[ModuleBase]) -> type[ModuleBase]:
    from . import register_module

    return register_module(module_cls)


register(MCPServersModule)
