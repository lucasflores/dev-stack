"""APM CLI commands — dev-stack apm install|audit."""
from __future__ import annotations

import json
from pathlib import Path

import click

from ..manifest import StackManifest, read_manifest
from ..modules.apm import APMModule
from .main import CLIContext, ExitCode, cli

MANIFEST_FILENAME = "dev-stack.toml"


@cli.group()
@click.pass_obj
def apm(ctx: CLIContext) -> None:  # pragma: no cover - declarative click entry point
    """APM-based MCP server management commands."""


@apm.command("install")
@click.option("--force", is_flag=True, help="Force reinstall even if lockfile is current.")
@click.pass_obj
def apm_install(ctx: CLIContext, force: bool) -> None:
    """Install MCP server packages from apm.yml manifest using APM CLI."""
    repo_root = Path.cwd()
    manifest = _load_manifest(repo_root)
    module = APMModule(repo_root, manifest.to_dict() if manifest else None)
    result = module.install(force=force)

    if ctx.json_output:
        payload = {
            "success": result.success,
            "message": result.message,
            "files_created": [str(f) for f in result.files_created],
            "warnings": result.warnings,
        }
        click.echo(json.dumps(payload))
    else:
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"✗ {result.message}", err=True)
        for f in result.files_created:
            click.echo(f"  {f}")
        for w in result.warnings:
            click.echo(f"  ! {w}", err=True)

    if not result.success:
        raise SystemExit(ExitCode.GENERAL_ERROR if result.files_created else ExitCode.AGENT_UNAVAILABLE)


@apm.command("audit")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json", "sarif", "markdown"]),
    default="text",
    help="Output format for the audit report.",
)
@click.option("--output", "output_file", type=click.Path(), default=None, help="Write report to file.")
@click.pass_obj
def apm_audit(ctx: CLIContext, fmt: str, output_file: str | None) -> None:
    """Run APM security audit on installed MCP server packages."""
    repo_root = Path.cwd()
    manifest = _load_manifest(repo_root)
    module = APMModule(repo_root, manifest.to_dict() if manifest else None)
    output_path = Path(output_file) if output_file else None
    result = module.audit(fmt=fmt, output=output_path)

    if ctx.json_output:
        payload = {
            "success": result.success,
            "message": result.message,
            "findings_count": 0 if result.success else len(result.warnings),
            "severity": "clean" if result.success else "findings",
            "report_path": str(output_path) if output_path else None,
        }
        click.echo(json.dumps(payload))
    else:
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"✗ {result.message}", err=True)
            for w in result.warnings:
                click.echo(f"  {w}", err=True)

    if not result.success:
        raise SystemExit(ExitCode.GENERAL_ERROR)


def _load_manifest(repo_root: Path) -> StackManifest | None:
    manifest_path = repo_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return read_manifest(manifest_path)
    except Exception:
        return None
