"""Visualization CLI — CodeBoarding integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from ..errors import CodeBoardingError
from ..modules.visualization import (
    CODEBOARDING_OUTPUT_DIR,
    DEFAULT_DEPTH_LEVEL,
    DEFAULT_TIMEOUT_SECONDS,
    INJECTION_LEDGER,
)
from ..visualization import codeboarding_runner
from ..visualization.output_parser import extract_mermaid, parse_components
from ..visualization.readme_injector import (
    InjectionLedger,
    inject_root_diagram,
)
from .main import CLIContext, ExitCode, cli

logger = logging.getLogger(__name__)


@cli.command("visualize")
@click.option("--incremental", is_flag=True, help="Only re-analyze changed files.")
@click.option(
    "--depth-level",
    type=int,
    default=DEFAULT_DEPTH_LEVEL,
    show_default=True,
    help="Number of decomposition levels (1 = top-level only).",
)
@click.option("--no-readme", is_flag=True, help="Run analysis without injecting diagrams into READMEs.")
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_TIMEOUT_SECONDS,
    show_default=True,
    help="Subprocess timeout in seconds for CodeBoarding CLI.",
)
@click.pass_obj
def visualize(
    ctx: CLIContext,
    incremental: bool,
    depth_level: int,
    no_readme: bool,
    timeout: int,
) -> None:
    """Generate architecture diagrams via CodeBoarding and inject into READMEs."""

    repo_root = Path.cwd()
    cb_dir = repo_root / CODEBOARDING_OUTPUT_DIR

    # ------------------------------------------------------------------
    # Step 1: Verify CLI availability
    # ------------------------------------------------------------------

    if not codeboarding_runner.check_cli_available():
        _emit_error(
            ctx,
            "CodeBoarding CLI not found on PATH.\nInstall via: pip install codeboarding\nThen run: codeboarding-setup",
            exit_code=ExitCode.AGENT_UNAVAILABLE,
        )
        raise SystemExit(ExitCode.AGENT_UNAVAILABLE)

    # ------------------------------------------------------------------
    # Step 2: Incremental gate (if requested)
    # ------------------------------------------------------------------

    from ..visualization.incremental import ManifestStore
    from ..visualization.scanner import SourceScanner

    manifest_store = ManifestStore(repo_root)

    if incremental:
        scanner = SourceScanner(repo_root)
        scan_result = scanner.scan()
        previous = manifest_store.load_manifest()
        current = manifest_store.build_manifest(scan_result.snapshots)
        changed_paths = manifest_store.changed_paths(previous, current)

        if not changed_paths:
            payload = {
                "status": "success",
                "skipped": True,
                "reason": "No files changed since last run",
                "files_scanned": len(current.files),
                "files_changed": 0,
                "incremental": True,
            }
            if ctx.json_output:
                click.echo(json.dumps(payload))
            else:
                click.echo("All diagrams up to date (no files changed).")
            return

    # ------------------------------------------------------------------
    # Step 3: Invoke CodeBoarding
    # ------------------------------------------------------------------

    try:
        result = codeboarding_runner.run(
            repo_root,
            depth_level=depth_level,
            incremental=incremental,
            timeout=timeout,
        )
    except CodeBoardingError as exc:
        _emit_error(ctx, str(exc), exit_code=ExitCode.GENERAL_ERROR)
        raise SystemExit(ExitCode.GENERAL_ERROR)

    if not result.success:
        msg = f"CodeBoarding exited with code {result.return_code}:\n{result.stderr}"
        _emit_error(ctx, msg, exit_code=ExitCode.GENERAL_ERROR)
        raise SystemExit(ExitCode.GENERAL_ERROR)

    # ------------------------------------------------------------------
    # Step 4: Parse output
    # ------------------------------------------------------------------

    try:
        components = parse_components(cb_dir)
    except CodeBoardingError as exc:
        _emit_error(ctx, str(exc), exit_code=ExitCode.GENERAL_ERROR)
        raise SystemExit(ExitCode.GENERAL_ERROR)

    # Extract overview Mermaid
    overview_mermaid = extract_mermaid(cb_dir / "overview.md")
    warnings: list[str] = []
    if overview_mermaid is None:
        warnings.append("No Mermaid diagram found in .codeboarding/overview.md")

    # ------------------------------------------------------------------
    # Step 5 & 6: Inject diagrams (unless --no-readme)
    # ------------------------------------------------------------------

    readmes_modified: list[str] = []
    diagrams_injected = 0
    ledger = InjectionLedger.load(cb_dir / INJECTION_LEDGER)
    ledger.clear()

    if not no_readme and overview_mermaid:
        if inject_root_diagram(repo_root, overview_mermaid, ledger):
            readmes_modified.append("README.md")
        diagrams_injected += 1

    # Sub-diagrams (Phase 5 will wire inject_component_diagrams here)
    if not no_readme:
        from ..visualization.readme_injector import inject_component_diagrams

        comp_result = inject_component_diagrams(repo_root, components, ledger)
        diagrams_injected += comp_result["diagrams_injected"]
        readmes_modified.extend(comp_result["readmes_modified"])

    # ------------------------------------------------------------------
    # Step 7: Save ledger and manifest
    # ------------------------------------------------------------------

    if not no_readme:
        ledger.save(cb_dir / INJECTION_LEDGER)

    # Always save manifest for future incremental comparisons
    try:
        scanner = SourceScanner(repo_root)
        scan_result = scanner.scan()
        current = manifest_store.build_manifest(scan_result.snapshots)
        manifest_store.save_manifest(current)
    except Exception:  # pragma: no cover
        logger.warning("Failed to save manifest for incremental tracking")

    # ------------------------------------------------------------------
    # Step 8: Report results
    # ------------------------------------------------------------------

    payload = {
        "status": "success",
        "depth_level": depth_level,
        "components_found": len(components),
        "diagrams_injected": diagrams_injected,
        "readmes_modified": readmes_modified,
        "incremental": incremental,
        "skipped": False,
        "codeboarding_output": str(CODEBOARDING_OUTPUT_DIR),
        "warnings": warnings,
    }

    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo(f"Visualization complete:")
        click.echo(f"  Components: {len(components)} found")
        click.echo(f"  Diagrams: {diagrams_injected} injected")
        if readmes_modified:
            click.echo("  READMEs modified:")
            for r in readmes_modified:
                click.echo(f"    - {r}")
        for w in warnings:
            click.echo(f"  Warning: {w}")


def _emit_error(ctx: CLIContext, message: str, *, exit_code: int = 1) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message, "exit_code": exit_code}))
    else:
        click.echo(f"Error: {message}", err=True)
