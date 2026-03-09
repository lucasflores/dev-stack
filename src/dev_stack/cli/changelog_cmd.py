"""``dev-stack changelog`` CLI command — generate or update CHANGELOG.md."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .main import cli


@cli.command("changelog")
@click.option("--unreleased", is_flag=True, default=True, help="Only changes since last tag (default).")
@click.option("--full", is_flag=True, help="Complete history from all tags.")
@click.option("--output", "output_file", default="CHANGELOG.md", show_default=True, help="Output file path.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.option("--verbose", is_flag=True, help="Verbose output.")
@click.pass_context
def changelog_cmd(
    ctx: click.Context,
    unreleased: bool,
    full: bool,
    output_file: str,
    as_json: bool,
    verbose: bool,
) -> None:
    """Generate or update CHANGELOG.md from conventional commit history."""
    from dev_stack.vcs.changelog import generate_changelog

    repo_root = Path.cwd()

    result = generate_changelog(
        repo_root=repo_root,
        unreleased=unreleased,
        full=full,
        output_file=output_file,
    )

    if as_json:
        if result.success:
            payload = {
                "status": "success",
                "output_file": result.output_file,
                "mode": result.mode,
                "versions_rendered": result.versions_rendered,
                "total_commits_processed": result.total_commits_processed,
                "ai_commits_annotated": result.ai_commits_annotated,
                "human_edited_annotated": result.human_edited_annotated,
                "git_cliff_version": result.git_cliff_version,
            }
        else:
            payload = {
                "status": "error",
                "error": result.error or "Unknown error",
            }
            if result.help:
                payload["help"] = result.help
        click.echo(json.dumps(payload, indent=2))
        if not result.success:
            ctx.exit(1)
        return

    if not result.success:
        click.echo(f"Error: {result.error}", err=True)
        if result.help:
            click.echo(f"Help: {result.help}", err=True)
        ctx.exit(1)
        return

    click.echo(f"Changelog generated: {output_file}")
    if verbose:
        click.echo(f"  Mode: {result.mode}")
        click.echo(f"  Versions rendered: {result.versions_rendered}")
        click.echo(f"  Commits processed: {result.total_commits_processed}")
        click.echo(f"  AI annotated: {result.ai_commits_annotated}")
        click.echo(f"  Human-edited annotated: {result.human_edited_annotated}")
