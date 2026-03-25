"""Implementation of the `dev-stack update` command."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click

from ..brownfield.conflict import (
    build_conflict_report,
    echo_conflict_summary,
    resolve_conflicts_interactively,
    serialize_conflicts,
)
from ..brownfield.rollback import create_rollback_tag
from ..errors import ManifestError
from ..manifest import ModuleDelta, ModuleEntry, StackManifest, read_manifest, write_manifest
from ..modules import (
    DEFAULT_GREENFIELD_MODULES,
    DEPRECATED_MODULES,
    instantiate_modules,
    latest_module_entries,
    resolve_module_names,
)
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

_UPDATE_MARKER = Path(".dev-stack") / "update-in-progress"


@cli.command("update", help="Update dev-stack configuration and module files in an existing repository.")
@click.option("--modules", "modules_csv", help="Comma-separated list of modules to update or add")
@click.option("--force", is_flag=True, help="Apply updates without prompting when conflicts arise")
@click.pass_obj
def update_command(ctx: CLIContext, modules_csv: str | None, force: bool) -> None:
    repo_root = Path.cwd()
    ensure_git_repo(repo_root)

    manifest_path = repo_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        emit_manifest_error(
            ctx,
            "dev-stack.toml not found. Run 'dev-stack init' before updating.",
            exit_code=ExitCode.GENERAL_ERROR,
        )

    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:
        emit_manifest_error(ctx, f"Unable to read manifest: {exc}", exit_code=ExitCode.GENERAL_ERROR)
        return

    requested_modules = parse_modules(modules_csv)
    if requested_modules:
        # Filter out deprecated modules from explicit --modules flag.
        active_requested = [m for m in requested_modules if m not in DEPRECATED_MODULES]
        deprecated_requested = [m for m in requested_modules if m in DEPRECATED_MODULES]
        if deprecated_requested:
            for name in deprecated_requested:
                msg = DEPRECATED_MODULES[name]
                if not ctx.json_output:
                    click.echo(f"\nℹ Module '{name}' has been removed.")
                    click.echo(f"  {msg}")
        if not active_requested:
            _emit_noop(ctx)
            return
        try:
            module_names = resolve_module_names(active_requested, include_defaults=False)
        except KeyError as exc:
            emit_manifest_error(ctx, str(exc), exit_code=ExitCode.GENERAL_ERROR)
    else:
        module_names = list(manifest.modules.keys())
        if not module_names:
            emit_manifest_error(
                ctx,
                "No modules installed. Use --modules to specify which modules to add.",
                exit_code=ExitCode.GENERAL_ERROR,
            )

    # FR-032: Detect new default modules not yet installed and prompt the user.
    if not requested_modules and not ctx.json_output:
        opted_in = _prompt_new_modules(manifest, ctx)
        if opted_in:
            module_names = resolve_module_names(module_names + opted_in, include_defaults=False)

    # Handle deprecated modules: emit info, mark in TOML, filter out.
    deprecated_found = _handle_deprecated_modules(manifest, module_names, ctx)
    module_names = [n for n in module_names if n not in DEPRECATED_MODULES]

    latest_entries = latest_module_entries(module_names or None)
    delta = manifest.diff_modules(latest_entries, module_names or None)
    targets = set(delta.added + delta.updated)
    modules_to_apply = [name for name in module_names if name in targets]

    if not modules_to_apply:
        if deprecated_found:
            write_manifest(manifest, manifest_path)
        _emit_noop(ctx)
        return

    module_instances = instantiate_modules(repo_root, manifest, modules_to_apply)
    module_lookup = {module.NAME: module for module in module_instances}
    detection_map, preview_lookup = collect_proposed_files(module_instances)
    conflict_report = build_conflict_report("update", repo_root, detection_map)
    conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    if ctx.dry_run:
        _emit_dry_run(ctx, delta, conflicts_payload)
        return

    marker_path = repo_root / _UPDATE_MARKER
    if marker_path.exists():
        _handle_incomplete_update(ctx)

    existing_conflicts = has_existing_conflicts(conflict_report)
    skip_map: dict[Path, tuple[bytes, int | None]] = {}
    merge_map: dict[Path, str] = {}
    if existing_conflicts and not force:
        if ctx.json_output:
            click.echo(
                json.dumps(
                    {
                        "status": "conflict",
                        "modules_added": delta.added,
                        "modules_updated": delta.updated,
                        "conflicts": conflicts_payload,
                    }
                )
            )
            raise SystemExit(ExitCode.CONFLICT)
        echo_conflict_summary(conflict_report, repo_root)
        skip_map, merge_map = resolve_conflicts_interactively(conflict_report, repo_root, preview_lookup)
        conflicts_payload = serialize_conflicts(conflict_report, repo_root)

    rollback_ref = create_rollback_tag(repo_root)
    _start_update_marker(marker_path)
    success = False
    try:
        _apply_module_updates(delta, module_lookup, skip_map, merge_map)
        _persist_manifest(manifest, latest_entries, delta, rollback_ref, manifest_path)
        success = True
    finally:
        if success and marker_path.exists():
            marker_path.unlink()

    _emit_success(ctx, delta, rollback_ref, conflicts_payload)


def _apply_module_updates(
    delta: ModuleDelta,
    module_lookup: dict[str, ModuleBase],
    skip_map: dict[Path, tuple[bytes, int | None]],
    merge_map: dict[Path, str],
) -> None:
    for name in delta.added:
        module = module_lookup.get(name)
        if module is None:
            continue
        module.install(force=True)
    for name in delta.updated:
        module = module_lookup.get(name)
        if module is None:
            continue
        module.update()
    apply_post_install_overrides(skip_map, merge_map)


def _persist_manifest(
    manifest: StackManifest,
    latest_entries: dict[str, ModuleEntry],
    delta: ModuleDelta,
    rollback_ref: str | None,
    manifest_path: Path,
) -> None:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    for name in delta.added:
        existing_entry = manifest.modules.get(name)
        manifest.modules[name] = ModuleEntry(
            version=latest_entries[name].version,
            installed=True,
            depends_on=list(existing_entry.depends_on) if existing_entry else [],
            config=dict(existing_entry.config) if existing_entry else {},
        )
    for name in delta.updated:
        entry = manifest.modules.get(name)
        if entry is None:
            manifest.modules[name] = ModuleEntry(version=latest_entries[name].version, installed=True)
        else:
            entry.version = latest_entries[name].version
            entry.installed = True
    manifest.last_updated = timestamp
    manifest.rollback_ref = rollback_ref
    write_manifest(manifest, manifest_path)


def _emit_noop(ctx: CLIContext) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "noop", "message": "No modules require updates."}))
    else:
        click.echo("No modules require updates.")


def _emit_success(ctx: CLIContext, delta: ModuleDelta, rollback_ref: str | None, conflicts_payload) -> None:
    payload = {
        "status": "success",
        "modules_added": delta.added,
        "modules_updated": delta.updated,
        "modules_removed": delta.removed,
        "rollback_ref": rollback_ref,
        "conflicts": conflicts_payload,
    }
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(
            "dev-stack update complete\n"
            f"- added: {', '.join(delta.added) or 'none'}\n"
            f"- updated: {', '.join(delta.updated) or 'none'}\n"
            f"- removed: {', '.join(delta.removed) or 'none'}"
        )


def _emit_dry_run(ctx: CLIContext, delta: ModuleDelta, conflicts) -> None:
    payload = {
        "status": "dry-run",
        "modules_added": delta.added,
        "modules_updated": delta.updated,
        "modules_removed": delta.removed,
        "conflicts": conflicts,
    }
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo("Dry run summary:")
        click.echo(f" - Added: {', '.join(delta.added) or 'none'}")
        click.echo(f" - Updated: {', '.join(delta.updated) or 'none'}")
        click.echo(f" - Removed: {', '.join(delta.removed) or 'none'}")


def _handle_incomplete_update(ctx: CLIContext) -> None:
    message = "A previous dev-stack update did not complete."
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
        raise SystemExit(ExitCode.GENERAL_ERROR)
    proceed = click.confirm(f"{message} Continue anyway?", default=False)
    if not proceed:
        click.echo("Run 'dev-stack rollback' to restore the repository before updating again.", err=True)
        raise SystemExit(ExitCode.GENERAL_ERROR)


def _start_update_marker(marker_path: Path) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        encoding="utf-8",
    )


def _prompt_new_modules(manifest: StackManifest, ctx: CLIContext) -> list[str]:
    """Detect default modules not yet installed and interactively offer them.

    Returns the list of module names the user opted in to.
    New modules are NEVER auto-installed (FR-032).
    """
    installed = set(manifest.modules.keys())
    new_defaults = [m for m in DEFAULT_GREENFIELD_MODULES if m not in installed]
    if not new_defaults:
        return []

    click.echo("\nNew modules are available since your last init:")
    opted_in: list[str] = []
    for name in new_defaults:
        if click.confirm(f"  Install '{name}'?", default=False):
            opted_in.append(name)
    if opted_in:
        click.echo(f"  → Adding: {', '.join(opted_in)}")
    else:
        click.echo("  → No new modules selected.")
    return opted_in


def _handle_deprecated_modules(
    manifest: StackManifest,
    module_names: list[str],
    ctx: CLIContext,
) -> list[str]:
    """Detect deprecated modules, emit info, mark them in the manifest.

    Returns list of deprecated module names found.
    """
    found: list[str] = []
    for name in module_names:
        message = DEPRECATED_MODULES.get(name)
        if message is None:
            continue
        found.append(name)
        entry = manifest.modules.get(name)
        if entry is not None:
            entry.deprecated = True
        if ctx.json_output:
            continue
        click.echo(f"\nℹ Module '{name}' has been removed.")
        for line in message.split(". "):
            line = line.strip().rstrip(".")
            if line:
                click.echo(f"  {line}.")
        click.echo(f"  Marking [modules.{name}] as deprecated in dev-stack.toml.")
    return found
