"""CLI entry point for dev-stack."""
from __future__ import annotations

import sys
from dataclasses import dataclass

import click


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
    """Show CLI configuration context."""

    if ctx.json_output:
        click.echo("{\"status\": \"ok\", \"mode\": \"version\"}")
    else:
        click.echo("dev-stack CLI ready")


# Register subcommands
from . import init_cmd, mcp_cmd, pipeline_cmd, rollback_cmd, status_cmd, update_cmd, visualize_cmd  # noqa: E402,F401
