"""Implementation of the ``dev-stack hooks`` command group."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import click

from ..modules.vcs_hooks import HookManifest, VcsHooksModule
from ..vcs import VcsConfig, load_vcs_config
from .main import CLIContext, ExitCode, cli


def _compute_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@cli.group("hooks")
def hooks_group() -> None:
    """Manage dev-stack git hooks."""


@hooks_group.command("status")
@click.pass_obj
def hooks_status(ctx: CLIContext) -> None:
    """Show the status of all managed git hooks."""
    repo_root = Path.cwd()
    config = load_vcs_config(repo_root)

    # Load manifest
    manifest_path = repo_root / ".dev-stack" / "hooks-manifest.json"
    manifest: HookManifest | None = None
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = HookManifest.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            manifest = None

    # Determine configured hooks
    configured_hooks: dict[str, bool] = {
        "commit-msg": config.hooks.commit_msg,
        "pre-push": config.hooks.pre_push,
        "pre-commit": config.hooks.pre_commit,
    }

    hooks_info: list[dict[str, Any]] = []
    overall_status = "not_installed"

    if manifest is not None:
        all_healthy = True
        for hook_name in ("commit-msg", "pre-push", "pre-commit"):
            entry = manifest.hooks.get(hook_name)
            if entry is not None:
                hook_path = repo_root / ".git" / "hooks" / hook_name
                if hook_path.exists():
                    actual_checksum = _compute_checksum(hook_path)
                    modified = actual_checksum != entry.checksum
                    hooks_info.append({
                        "name": hook_name,
                        "installed": True,
                        "path": f".git/hooks/{hook_name}",
                        "checksum_expected": entry.checksum,
                        "checksum_actual": actual_checksum,
                        "modified": modified,
                        "installed_at": entry.installed_at,
                        "template_version": entry.template_version,
                    })
                    if modified:
                        all_healthy = False
                else:
                    hooks_info.append({
                        "name": hook_name,
                        "installed": False,
                        "configured": configured_hooks.get(hook_name, False),
                    })
                    all_healthy = False
            else:
                hooks_info.append({
                    "name": hook_name,
                    "installed": False,
                    "configured": configured_hooks.get(hook_name, False),
                })

        overall_status = "healthy" if all_healthy else "degraded"
    else:
        for hook_name in ("commit-msg", "pre-push", "pre-commit"):
            hooks_info.append({
                "name": hook_name,
                "installed": False,
                "configured": configured_hooks.get(hook_name, False),
            })

    payload: dict[str, Any] = {
        "status": overall_status,
        "manifest_path": ".dev-stack/hooks-manifest.json",
        "hooks": hooks_info,
    }

    # Add signing status (T055)
    from dev_stack.vcs.signing import find_ssh_public_key, supports_ssh_signing

    signing_info: dict[str, Any] = {
        "enabled": config.signing.enabled,
        "enforcement": config.signing.enforcement,
        "key": config.signing.key or find_ssh_public_key(),
        "git_supports_ssh_signing": supports_ssh_signing(),
    }
    payload["signing"] = signing_info

    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        _emit_human_hooks_status(payload)


def _emit_human_hooks_status(payload: dict[str, Any]) -> None:
    """Render hooks status in human-readable format."""
    click.echo("Hook Status")
    click.echo("─" * 43)

    for hook in payload["hooks"]:
        name = hook["name"]
        if hook.get("installed"):
            if hook.get("modified"):
                icon = "⚠"
                detail = "(manually modified)"
            else:
                icon = "✓"
                detail = "(unmodified)"
            click.echo(f"  {name:<14} {icon} installed  {detail}")
        else:
            configured = hook.get("configured", False)
            if configured:
                click.echo(f"  {name:<14} ○ not installed (enabled in config)")
            else:
                click.echo(f"  {name:<14} ○ not installed (disabled in config)")

    # Signing section
    signing = payload.get("signing", {})
    click.echo()
    click.echo("Signing")
    click.echo("─" * 43)
    if signing.get("enabled"):
        click.echo(f"  Enabled:      ✓ yes")
        click.echo(f"  Enforcement:  {signing.get('enforcement', 'warn')}")
        key = signing.get("key")
        click.echo(f"  Key:          {key or '(none detected)'}")
        git_ok = signing.get("git_supports_ssh_signing", False)
        icon = "✓" if git_ok else "✗"
        click.echo(f"  Git >= 2.34:  {icon} {'yes' if git_ok else 'no (SSH signing unavailable)'}")
    else:
        click.echo("  Enabled:      ○ no")

    click.echo()
