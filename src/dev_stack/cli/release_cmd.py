"""``dev-stack release`` — semantic release versioning."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .main import cli


@cli.command("release")
@click.option("--dry-run", is_flag=True, help="Preview without making changes.")
@click.option(
    "--bump",
    type=click.Choice(["major", "minor", "patch"]),
    default=None,
    help="Override inferred bump type.",
)
@click.option("--no-tag", is_flag=True, help="Skip creating git tag.")
@click.option("--json-output", "--json", "json_out", is_flag=True, help="JSON output.")
def release_cmd(dry_run: bool, bump: str | None, no_tag: bool, json_out: bool) -> None:
    """Perform a semantic release."""
    from dev_stack.vcs.release import execute_release, prepare_release

    repo_root = Path.cwd()

    ctx = prepare_release(repo_root=repo_root, bump_override=bump)  # type: ignore[arg-type]

    # Count commit types
    type_counts: dict[str, int] = {}
    for c in ctx.commits:
        type_counts[c.type] = type_counts.get(c.type, 0) + 1

    breaking_count = sum(1 for c in ctx.commits if c.is_breaking)

    # Check if blocked by hard failures
    if ctx.hard_failures:
        if json_out:
            click.echo(json.dumps({
                "status": "blocked",
                "reason": "Hard pipeline failures detected in commit range",
                "hard_failures": [
                    {
                        "sha": hf.sha,
                        "subject": hf.subject,
                        "failed_stages": hf.failed_stages,
                    }
                    for hf in ctx.hard_failures
                ],
            }, indent=2))
        else:
            click.secho("Release blocked: hard pipeline failures detected", fg="red", bold=True)
            for hf in ctx.hard_failures:
                click.echo(f"  • {hf.sha} {hf.subject} — {', '.join(hf.failed_stages)}")
        sys.exit(6)

    if dry_run:
        if json_out:
            click.echo(json.dumps({
                "status": "dry_run",
                "current_version": ctx.current_version,
                "next_version": ctx.next_version,
                "bump_type": ctx.bump_type,
                "commits_analyzed": len(ctx.commits),
                "breaking_changes": breaking_count,
                "tag_created": None,
                "pyproject_updated": False,
                "changelog_updated": False,
                "hard_failures": [],
            }, indent=2))
        else:
            click.echo("Release Summary")
            click.echo("─" * 40)
            click.echo(f"  Current version:  {ctx.current_version}")
            click.echo(f"  Next version:     {ctx.next_version}")
            click.echo(f"  Bump type:        {ctx.bump_type}")
            counts_str = ", ".join(f"{n} {t}" for t, n in sorted(type_counts.items()))
            click.echo(f"  Commits:          {len(ctx.commits)} ({counts_str})")
            click.echo(f"  Breaking changes: {breaking_count}")
            click.echo(f"  Hard failures:    0")
            click.echo()
            click.echo("Actions (--dry-run, no changes made):")
            click.echo(f"  • Update pyproject.toml version → {ctx.next_version}")
            click.echo(f"  • Update CHANGELOG.md")
            if not no_tag:
                click.echo(f"  • Create tag {ctx.tag_name}")
        return

    # Execute the release
    results = execute_release(ctx, repo_root=repo_root, no_tag=no_tag)

    if json_out:
        click.echo(json.dumps({
            "status": "success",
            "current_version": ctx.current_version,
            "next_version": ctx.next_version,
            "bump_type": ctx.bump_type,
            "commits_analyzed": len(ctx.commits),
            "breaking_changes": breaking_count,
            "tag_created": results.get("tag_created"),
            "pyproject_updated": results.get("pyproject_updated", False),
            "changelog_updated": results.get("changelog_updated", False),
            "hard_failures": [],
        }, indent=2))
    else:
        click.secho(f"Released {ctx.tag_name}", fg="green", bold=True)
        click.echo(f"  Version: {ctx.current_version} → {ctx.next_version}")
        if results.get("pyproject_updated"):
            click.echo("  ✓ pyproject.toml updated")
        if results.get("changelog_updated"):
            click.echo("  ✓ CHANGELOG.md updated")
        if results.get("tag_created"):
            click.echo(f"  ✓ Tag {results['tag_created']} created")
