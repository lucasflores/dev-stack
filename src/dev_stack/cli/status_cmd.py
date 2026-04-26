"""Implementation of the `dev-stack status` command."""
from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path
from typing import Any

import click

from ..config import detect_agent
from ..errors import ManifestError
from ..manifest import ISO_FORMAT, StackManifest, read_manifest
from ..modules import available_modules, instantiate_modules
from ..modules.base import ModuleStatus
from ._constants import MANIFEST_FILENAME
from .main import CLIContext, ExitCode, cli

PIPELINE_STATE_FILE = Path(".dev-stack") / "pipeline" / "last-run.json"


@cli.command("status")
@click.pass_obj
def status_command(ctx: CLIContext) -> None:
    """Display manifest, agent, module, and pipeline health."""

    repo_root = Path.cwd()
    manifest = _load_manifest(ctx, repo_root)
    module_statuses = _collect_module_statuses(repo_root, manifest)
    agent_info = detect_agent(manifest)
    agent_available = agent_info.cli != "none" and bool(agent_info.path)
    pipeline_state = _load_pipeline_state(repo_root)

    payload = {
        "manifest_version": manifest.version,
        "mode": manifest.mode or "unknown",
        "initialized": manifest.initialized.astimezone(timezone.utc).strftime(ISO_FORMAT),
        "last_updated": manifest.last_updated.astimezone(timezone.utc).strftime(ISO_FORMAT),
        "agent": {
            "cli": agent_info.cli,
            "status": "available" if agent_available else "unavailable",
            "path": agent_info.path,
        },
        "modules": {
            name: _status_to_payload(status)
            for name, status in sorted(module_statuses.items())
        },
        "last_pipeline_run": pipeline_state.get("timestamp") if pipeline_state else None,
        "rollback_available": bool(manifest.rollback_ref),
        "rollback_ref": manifest.rollback_ref,
        "pipeline": pipeline_state,
    }

    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        _emit_human_status(payload)


# ---------------------------------------------------------------------------

def _load_manifest(ctx: CLIContext, repo_root: Path) -> StackManifest:
    manifest_path = repo_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        _emit_error(ctx, "dev-stack.toml not found in this repository", ExitCode.GENERAL_ERROR)
    try:
        return read_manifest(manifest_path)
    except ManifestError as exc:
        _emit_error(ctx, f"Unable to read manifest: {exc}", ExitCode.GENERAL_ERROR)
        raise  # Unreachable, but keeps type checkers happy


def _collect_module_statuses(repo_root: Path, manifest: StackManifest) -> dict[str, ModuleStatus]:
    statuses: dict[str, ModuleStatus] = {}
    available = set(available_modules())
    installed_names = [
        name for name, entry in manifest.modules.items() if entry.installed
    ]
    missing = [name for name in installed_names if name not in available]
    for name in missing:
        entry = manifest.modules.get(name)
        statuses[name] = ModuleStatus(
            name=name,
            installed=True,
            version=entry.version if entry else "unknown",
            healthy=False,
            issue="Module implementation missing",
        )
    resolved_names = [name for name in installed_names if name not in missing]
    if resolved_names:
        instances = instantiate_modules(repo_root, manifest, resolved_names)
        for instance in instances:
            try:
                status = instance.verify()
            except Exception as exc:  # pragma: no cover - defensive fail-safe
                status = ModuleStatus(
                    name=instance.NAME,
                    installed=True,
                    version=instance.version,
                    healthy=False,
                    issue=str(exc) or exc.__class__.__name__,
                )
            statuses[instance.NAME] = status
    # include non-installed entries for completeness
    for name, entry in manifest.modules.items():
        if entry.installed or name in statuses:
            continue
        statuses[name] = ModuleStatus(
            name=name,
            installed=False,
            version=entry.version,
            healthy=False,
            issue="Module not installed",
        )
    return statuses


def _load_pipeline_state(repo_root: Path) -> dict[str, Any] | None:
    state_path = repo_root / PIPELINE_STATE_FILE
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _status_to_payload(status: ModuleStatus) -> dict[str, Any]:
    return {
        "installed": status.installed,
        "version": status.version,
        "healthy": status.healthy,
        "issue": status.issue,
        "config": status.config or {},
    }


def _emit_human_status(payload: dict[str, Any]) -> None:
    click.echo(f"dev-stack v{payload['manifest_version']} ({payload['mode']})")
    agent = payload["agent"]
    click.echo(f"Agent: {agent['cli']} ({agent['status']})")
    click.echo("\nModules:")
    modules = payload["modules"]
    for name in sorted(modules.keys()):
        status = modules[name]
        indicator = "OK" if status["healthy"] else "!!"
        issue = status["issue"] or "healthy"
        click.echo(f"  [{indicator}] {name} v{status['version']} - {issue}")
    last_run = payload["last_pipeline_run"] or "never"
    click.echo(f"\nLast pipeline run: {last_run}")
    if payload["rollback_available"]:
        click.echo(f"Rollback available: {payload['rollback_ref']}")
    else:
        click.echo("Rollback available: none")


def _emit_error(ctx: CLIContext, message: str, exit_code: int) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)
    raise SystemExit(exit_code)