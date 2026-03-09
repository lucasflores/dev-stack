"""``dev-stack pr`` CLI command — generate and optionally create PRs."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from .main import cli


@cli.command("pr")
@click.option("--dry-run", is_flag=True, help="Print rendered Markdown without creating PR.")
@click.option("--base", default="main", show_default=True, help="Base branch for comparison.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.option("--verbose", is_flag=True, help="Verbose output.")
@click.pass_context
def pr_cmd(ctx: click.Context, dry_run: bool, base: str, as_json: bool, verbose: bool) -> None:
    """Generate a PR description from branch commits."""
    from dev_stack.vcs.commit_parser import parse_commits
    from dev_stack.vcs.pr import build_pr_description, render_pr_markdown

    repo_root = Path.cwd()

    # Determine current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_root),
        )
        branch = result.stdout.strip() if result.returncode == 0 else "HEAD"
    except Exception:
        branch = "HEAD"

    # Parse commits
    commits = parse_commits(base=base, head="HEAD", repo_root=repo_root)

    if not commits:
        if as_json:
            click.echo(json.dumps({"status": "error", "error": "No changes to create a PR for"}))
        else:
            click.echo("No changes to create a PR for.", err=True)
        ctx.exit(1)
        return

    desc = build_pr_description(commits, branch=branch, base=base)
    md = render_pr_markdown(desc)

    ai_pct = round(desc.ai_commits / desc.total_commits * 100) if desc.total_commits > 0 else 0

    if as_json:
        payload: dict = {
            "status": "dry_run" if dry_run else "printed",
            "branch": branch,
            "base": base,
            "total_commits": desc.total_commits,
            "ai_commits": desc.ai_commits,
            "human_commits": desc.total_commits - desc.ai_commits,
            "edited_commits": desc.edited_count,
            "spec_refs": desc.spec_refs,
            "task_refs": desc.task_refs,
            "agents": desc.agents,
            "pipeline_status": desc.pipeline_status,
            "pr_url": None,
            "description_md": md,
        }

    if dry_run:
        if as_json:
            payload["status"] = "dry_run"
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(md)
        return

    # Detect PR CLI tool
    pr_url: str | None = None
    status = "printed"

    if shutil.which("gh"):
        try:
            gh_result = subprocess.run(
                ["gh", "pr", "create", "--title", desc.title, "--body", md, "--base", base],
                capture_output=True, text=True, timeout=60,
                cwd=str(repo_root),
            )
            if gh_result.returncode == 0:
                pr_url = gh_result.stdout.strip()
                status = "created"
            else:
                # Fallback to printing
                if verbose:
                    click.echo(f"gh pr create failed: {gh_result.stderr}", err=True)
                click.echo(md)
        except Exception as exc:
            if verbose:
                click.echo(f"gh error: {exc}", err=True)
            click.echo(md)
    elif shutil.which("glab"):
        try:
            glab_result = subprocess.run(
                ["glab", "mr", "create", "--title", desc.title, "--description", md,
                 "--source-branch", branch, "--target-branch", base],
                capture_output=True, text=True, timeout=60,
                cwd=str(repo_root),
            )
            if glab_result.returncode == 0:
                pr_url = glab_result.stdout.strip()
                status = "created"
            else:
                if verbose:
                    click.echo(f"glab mr create failed: {glab_result.stderr}", err=True)
                click.echo(md)
        except Exception as exc:
            if verbose:
                click.echo(f"glab error: {exc}", err=True)
            click.echo(md)
    else:
        if not as_json:
            click.echo("Neither 'gh' nor 'glab' CLI found — printing PR description:\n", err=True)
        click.echo(md)

    if as_json:
        payload["status"] = status
        payload["pr_url"] = pr_url
        click.echo(json.dumps(payload, indent=2))
