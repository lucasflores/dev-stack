"""Implementation of the `dev-stack rollback` command."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import click

from ..brownfield.rollback import delete_tags, list_rollback_tags, restore_rollback
from ..errors import ManifestError, RollbackError
from ..manifest import read_manifest, write_manifest
from ._constants import MANIFEST_FILENAME
from .main import CLIContext, ExitCode, cli


@cli.command("rollback")
@click.option("--ref", "target_ref", help="Rollback tag to restore")
@click.pass_obj
def rollback_command(ctx: CLIContext, target_ref: str | None) -> None:
    """Restore repository state using the last rollback tag."""

    repo_root = Path.cwd()
    manifest_path = repo_root / MANIFEST_FILENAME
    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:  # pragma: no cover - defensive
        _emit_error(ctx, f"Unable to read manifest: {exc}", ExitCode.ROLLBACK_FAILURE)
        return

    ref_to_restore = target_ref or manifest.rollback_ref
    if not ref_to_restore:
        _emit_error(ctx, "No rollback reference available.", ExitCode.ROLLBACK_FAILURE)
        return

    if ctx.dry_run:
        _emit_dry_run(ctx, ref_to_restore)
        return

    try:
        restore_rollback(repo_root, ref_to_restore)
    except RollbackError as exc:
        _emit_error(ctx, str(exc), ExitCode.ROLLBACK_FAILURE)
        return

    tags_removed = _cleanup_tags(repo_root, ref_to_restore)

    if manifest_path.exists():
        manifest.last_updated = datetime.now(timezone.utc)
        manifest.rollback_ref = None
        write_manifest(manifest, manifest_path)

    _emit_success(ctx, ref_to_restore, tags_removed)


def _cleanup_tags(repo_root: Path, ref: str) -> Sequence[str]:
    try:
        tags = list_rollback_tags(repo_root)
    except RollbackError:
        return []
    to_delete = [tag for tag in tags if tag >= ref]
    if to_delete:
        delete_tags(repo_root, to_delete)
    return to_delete


def _emit_success(ctx: CLIContext, ref: str, tags_removed: Sequence[str]) -> None:
    payload = {
        "status": "success",
        "restored_ref": ref,
        "tags_cleaned": list(tags_removed),
    }
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(f"Rollback complete → {ref}")
        if tags_removed:
            click.echo("Removed tags:")
            for tag in tags_removed:
                click.echo(f" - {tag}")


def _emit_dry_run(ctx: CLIContext, ref: str) -> None:
    payload = {"status": "dry-run", "restored_ref": ref}
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(f"Rollback dry run → would restore {ref}")


def _emit_error(ctx: CLIContext, message: str, exit_code: int) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)
    raise SystemExit(exit_code)