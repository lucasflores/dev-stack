"""CLI entry point for dev-stack."""
from __future__ import annotations

import sys
from dataclasses import dataclass

import click


def _get_version() -> str:
    from importlib.metadata import version, PackageNotFoundError

    try:
        return version("dev-stack")
    except PackageNotFoundError:
        import dev_stack

        return getattr(dev_stack, "__version__", "0.0.0-dev")


@dataclass(slots=True)
class CLIContext:
    json_output: bool
    verbose: bool
    dry_run: bool
    color_enabled: bool


class ExitCode:
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_USAGE = 2
    CONFLICT = 3
    AGENT_UNAVAILABLE = 4
    PIPELINE_FAILURE = 5
    ROLLBACK_FAILURE = 10


@click.group()
@click.version_option(
    version=_get_version(),
    prog_name="dev-stack",
    message="%(prog)s %(version)s",
)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging to stderr.")
@click.option("--dry-run", is_flag=True, help="Preview actions without writing changes.")
@click.pass_context
def cli(ctx: click.Context, json_output: bool, verbose: bool, dry_run: bool) -> None:
    """Dev Stack automation CLI."""

    color_enabled = sys.stdout.isatty()
    ctx.obj = CLIContext(
        json_output=json_output,
        verbose=verbose,
        dry_run=dry_run,
        color_enabled=color_enabled,
    )


@cli.command()
@click.pass_obj
def version(ctx: CLIContext) -> None:
    """Show CLI version and configuration context."""

    ver = _get_version()
    if ctx.json_output:
        import json

        click.echo(json.dumps({"status": "ok", "version": ver, "prog_name": "dev-stack"}))
    else:
        click.echo(f"dev-stack {ver}")


# Register subcommands
from . import apm_cmd, changelog_cmd, hooks_cmd, init_cmd, mcp_cmd, pipeline_cmd, pr_cmd, release_cmd, rollback_cmd, status_cmd, update_cmd, visualize_cmd  # noqa: E402,F401
