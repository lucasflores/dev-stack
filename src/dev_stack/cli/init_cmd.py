"""Implementation of the `dev-stack init` command."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import click

from ..brownfield.conflict import (
    ConflictReport,
    ConflictType,
    build_conflict_report,
    echo_conflict_summary,
    resolve_conflicts_interactively,
    serialize_conflicts,
)
from ..brownfield.rollback import create_rollback_tag
from ..config import AgentInfo, detect_agent
from ..errors import ManifestError
from ..manifest import AgentConfig, StackManifest, create_default, read_manifest, write_manifest
from ..modules import instantiate_modules, resolve_module_names
from ..modules.base import ModuleBase
from ._constants import MANIFEST_FILENAME
from ._shared import (
    apply_post_install_overrides,
    collect_proposed_files,
    emit_manifest_error,
    ensure_git_repo,
    has_existing_conflicts,
    parse_modules,
)
from .main import CLIContext, ExitCode, cli


@cli.command("init")
@click.option("--modules", "modules_csv", help="Comma-separated list of modules to install")
@click.option("--force", is_flag=True, help="Overwrite existing files managed by dev-stack")

@click.pass_obj
def init_command(ctx: CLIContext, modules_csv: str | None, force: bool) -> None:
    """Initialize a repository with dev-stack automation."""

    repo_root = Path.cwd()

    ensure_git_repo(repo_root)

    manifest_path = repo_root / MANIFEST_FILENAME
    already_initialized = manifest_path.exists()
    existing_manifest: StackManifest | None = None
    if already_initialized:
        try:
            existing_manifest = read_manifest(manifest_path)
        except ManifestError as exc:
            emit_manifest_error(ctx, f"Unable to read existing manifest: {exc}", exit_code=ExitCode.GENERAL_ERROR)
            return
    if already_initialized and not force:
        _report_already_initialized(ctx)
        raise SystemExit(ExitCode.GENERAL_ERROR)

    requested_modules = parse_modules(modules_csv)
    if requested_modules:
        module_names = resolve_module_names(requested_modules, include_defaults=False)
    elif existing_manifest:
        module_names = list(existing_manifest.modules.keys())
    else:
        module_names = resolve_module_names(include_defaults=True)

    if existing_manifest and not requested_modules:
        manifest = existing_manifest
    else:
        manifest = create_default(module_names)

    should_write_manifest = not already_initialized or bool(requested_modules)
    should_create_rollback = not ctx.dry_run and should_write_manifest

    agent_info = detect_agent(manifest)
    manifest.agent = AgentConfig(cli=agent_info.cli, path=agent_info.path)

    module_instances = instantiate_modules(repo_root, manifest, module_names)
    detection_map, preview_lookup = collect_proposed_files(module_instances)
    conflict_report = build_conflict_report("init", repo_root, detection_map)
    existing_conflicts = has_existing_conflicts(conflict_report)
    mode = _determine_mode(already_initialized, existing_conflicts)
    manifest.mode = mode

    if ctx.dry_run:
        _emit_dry_run_summary(ctx, repo_root, manifest_path, mode, module_names, conflict_report)
        return

    skip_map: dict[Path, tuple[bytes, int | None]] = {}
    merge_map: dict[Path, str] = {}
    conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    if existing_conflicts and not force:
        if ctx.json_output:
            payload = {
                "status": "conflict",
                "mode": mode,
                "manifest_path": str(manifest_path),
                "modules": module_names,
                "conflicts": conflicts_payload,
            }
            click.echo(json.dumps(payload))
            raise SystemExit(ExitCode.CONFLICT)
        echo_conflict_summary(conflict_report, repo_root)
        skip_map, merge_map = resolve_conflicts_interactively(conflict_report, repo_root, preview_lookup)
        conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    rollback_ref = manifest.rollback_ref
    if should_create_rollback:
        rollback_ref = create_rollback_tag(repo_root)
    if not ctx.dry_run:
        effective_force = force or existing_conflicts
        _install_modules(module_instances, force=effective_force)
        apply_post_install_overrides(skip_map, merge_map)
        if should_write_manifest:
            manifest.rollback_ref = rollback_ref
            write_manifest(manifest, manifest_path)

    _emit_init_result(
        ctx,
        mode=mode,
        modules_installed=module_names,
        manifest_path=str(manifest_path),
        rollback_ref=rollback_ref,
        agent=agent_info,
        conflicts=conflicts_payload,
    )
def _install_modules(modules: Sequence[ModuleBase], force: bool) -> None:
    for module in modules:
        module.install(force=force)


def _emit_init_result(
    ctx: CLIContext,
    *,
    mode: str,
    modules_installed: Sequence[str],
    manifest_path: str,
    rollback_ref: str | None,
    agent: AgentInfo,
    conflicts: list[dict[str, str | None]] | None = None,
) -> None:
    payload = {
        "status": "success",
        "mode": mode,
        "manifest_path": manifest_path,
        "modules_installed": list(modules_installed),
        "rollback_ref": rollback_ref,
        "agent": {"cli": agent.cli, "path": agent.path},
    }
    payload["conflicts"] = conflicts or []
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(
            f"dev-stack init ({mode})\n- manifest: {manifest_path}\n- modules: {', '.join(modules_installed) or 'none'}"
        )


def _determine_mode(already_initialized: bool, has_conflicts: bool) -> str:
    if already_initialized:
        return "reinit"
    if has_conflicts:
        return "brownfield"
    return "greenfield"


def _emit_dry_run_summary(
    ctx: CLIContext,
    repo_root: Path,
    manifest_path: Path,
    mode: str,
    modules: Sequence[str],
    report: ConflictReport,
) -> None:
    conflicts_payload = serialize_conflicts(report, repo_root)
    new_files: list[str] = []
    for conflict in report.conflicts:
        if conflict.conflict_type != ConflictType.NEW:
            continue
        try:
            rel = conflict.path.relative_to(repo_root)
        except ValueError:
            rel = conflict.path
        new_files.append(str(rel))
    payload = {
        "status": "dry-run",
        "mode": mode,
        "manifest_path": str(manifest_path),
        "modules": list(modules),
        "conflicts": conflicts_payload,
        "new_files": new_files,
    }
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo("Dry run summary:")
        click.echo(f" - Mode: {mode}")
        click.echo(f" - Manifest: {manifest_path}")
        click.echo(f" - Modules: {', '.join(modules) or 'none'}")
        echo_conflict_summary(report, repo_root)
        if new_files:
            click.echo("Files to be created:")
            for path in new_files:
                click.echo(f" - {path}")


def _report_already_initialized(ctx: CLIContext) -> None:
    message = (
        "Repository already has dev-stack.toml. Use --force to reinitialize or run 'dev-stack update'."
    )
    if ctx.json_output:
        payload = {"status": "error", "message": message}
        click.echo(json.dumps(payload))
    else:
        click.echo(message, err=True)



