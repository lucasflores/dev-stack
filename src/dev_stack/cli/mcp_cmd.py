"""MCP server CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import click

from ..errors import AgentUnavailableError, ConfigError, ManifestError
from ..manifest import StackManifest, read_manifest
from ..modules.mcp_servers import MCPServersModule, _ServerDefinition
from .main import CLIContext, ExitCode, cli

MANIFEST_FILENAME = "dev-stack.toml"


@cli.group()
@click.pass_obj
def mcp(ctx: CLIContext) -> None:  # pragma: no cover - declarative click entry point
    """MCP server management commands."""


@mcp.command("install")
@click.option("--server", "servers", multiple=True, help="Install only specific MCP server(s).")
@click.option("--force", is_flag=True, help="Overwrite existing config files.")
@click.pass_obj
def mcp_install(ctx: CLIContext, servers: tuple[str, ...], force: bool) -> None:
    """Generate MCP server configuration for the detected agent."""

    repo_root = Path.cwd()
    manifest = _load_manifest(repo_root)
    module = MCPServersModule(repo_root, manifest.to_dict() if manifest else None)
    try:
        result, agent, definitions = module.install_selected(servers or None, force=force)
    except AgentUnavailableError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.AGENT_UNAVAILABLE)
    except ConfigError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.INVALID_USAGE)

    env_report = module.env_report(definitions)
    config_path = module.agent_output_path(agent)
    payload = _build_install_payload(agent, definitions, env_report, result, config_path)
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        _emit_install_human(payload, result.warnings)


@mcp.command("verify")
@click.option("--server", "servers", multiple=True, help="Verify only specific MCP server(s).")
@click.pass_obj
def mcp_verify(ctx: CLIContext, servers: tuple[str, ...]) -> None:
    """Verify MCP server configuration and dependencies."""

    repo_root = Path.cwd()
    manifest = _load_manifest(repo_root)
    module = MCPServersModule(repo_root, manifest.to_dict() if manifest else None)
    try:
        agent = module.resolve_agent()
    except AgentUnavailableError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.AGENT_UNAVAILABLE)
    try:
        definitions = module.get_server_definitions(servers or None)
    except ConfigError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.INVALID_USAGE)

    env_report = module.env_report(definitions)
    reports = [_build_server_report(module, definition, env_report) for definition in definitions]
    config_path = module.agent_output_path(agent.cli)
    payload = _build_verify_payload(agent.cli, reports, config_path)
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        _emit_verify_human(payload)

    if payload["status"] == "all_fail":
        raise SystemExit(ExitCode.GENERAL_ERROR)


# ---------------------------------------------------------------------------


def _load_manifest(repo_root: Path) -> StackManifest | None:
    manifest_path = repo_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return read_manifest(manifest_path)
    except ManifestError:
        return None


def _build_install_payload(
    agent: str,
    definitions: Sequence[_ServerDefinition],
    env_report: dict[str, bool],
    result,
    config_path: Path | None,
) -> dict:
    servers: list[dict[str, object]] = []
    for definition in definitions:
        env_status = {var: env_report.get(var, True) for var in definition.env}
        missing = [var for var, present in env_status.items() if not present]
        servers.append(
            {
                "name": definition.name,
                "package": definition.package,
                "env": env_status,
                "missing_vars": missing,
                "description": definition.description,
            }
        )
    status = "success"
    if any(server["missing_vars"] for server in servers):
        status = "partial"
    payload = {
        "status": status,
        "agent": agent,
        "config_path": str(config_path) if config_path else None,
        "servers": servers,
        "warnings": result.warnings,
    }
    return payload


def _build_server_report(
    module: MCPServersModule,
    definition: _ServerDefinition,
    env_report: dict[str, bool],
) -> dict:
    missing = [var for var in definition.env if not env_report.get(var, True)]
    health_status, health_message = module.run_health_check(definition)
    server_status = "fail" if missing or health_status == "fail" else "pass"
    return {
        "name": definition.name,
        "status": server_status,
        "health_status": health_status,
        "health_message": health_message,
        "missing_vars": missing,
    }


def _build_verify_payload(agent: str, reports: Sequence[dict], config_path: Path | None) -> dict:
    total = len(reports)
    failures = sum(1 for report in reports if report["status"] == "fail")
    passes = sum(1 for report in reports if report["status"] == "pass")
    if failures == 0 and passes == total:
        overall = "all_pass"
    elif failures == total:
        overall = "all_fail"
    else:
        overall = "partial"
    return {
        "status": overall,
        "agent": agent,
        "config_path": str(config_path) if config_path else None,
        "servers": list(reports),
    }


def _emit_install_human(payload: dict, warnings: Sequence[str]) -> None:
    click.echo(f"MCP servers configured for agent: {payload['agent']}")
    if payload.get("config_path"):
        click.echo(f" - Config written to {payload['config_path']}")
    for server in payload["servers"]:
        missing = server["missing_vars"]
        status = "ready" if not missing else f"missing env: {', '.join(missing)}"
        click.echo(f" - {server['name']}: {status}")
    for warning in warnings:
        click.echo(f" ! {warning}", err=True)


def _emit_verify_human(payload: dict) -> None:
    click.echo(f"MCP verify status: {payload['status']}")
    if payload.get("config_path"):
        click.echo(f" - Config path: {payload['config_path']}")
    for server in payload["servers"]:
        health = server["health_status"]
        miss = server["missing_vars"]
        extra = "ok" if not miss else f"missing {', '.join(miss)}"
        click.echo(f" - {server['name']}: {server['status']} ({health}, {extra})")


def _emit_error(ctx: CLIContext, message: str) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)
