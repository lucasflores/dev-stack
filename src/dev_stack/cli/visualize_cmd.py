"""Visualization CLI — Understand-Anything graph freshness validation."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import click

from ..errors import VisualizationError
from ..modules.visualization import (
    KNOWLEDGE_GRAPH_FILE,
    SUPPORTED_PLUGIN_EXPERIENCES,
    UNDERSTAND_OUTPUT_DIR,
    DEFAULT_DEPTH_LEVEL,
    DEFAULT_TIMEOUT_SECONDS,
)
from ..visualization import graph_policy, understand_runner
from .main import CLIContext, ExitCode, cli

logger = logging.getLogger(__name__)


@cli.command("visualize")
@click.option("--incremental", is_flag=True, help="Only re-analyze changed files.")
@click.option(
    "--depth-level",
    type=int,
    default=DEFAULT_DEPTH_LEVEL,
    show_default=True,
    help="Compatibility option retained for existing workflows.",
)
@click.option(
    "--no-readme",
    is_flag=True,
    help="Compatibility option retained; README injection is no longer performed.",
)
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_TIMEOUT_SECONDS,
    show_default=True,
    help="Compatibility option retained for existing workflows.",
)
@click.option(
    "--plugin",
    type=str,
    default="auto",
    show_default=True,
    help="Plugin workflow context (auto, copilot, claude).",
)
@click.pass_obj
def visualize(
    ctx: CLIContext,
    incremental: bool,
    depth_level: int,
    no_readme: bool,
    timeout: int,
    plugin: str,
) -> None:
    """Validate committed Understand-Anything artifacts and freshness policy."""

    repo_root = Path.cwd()
    graph_dir = repo_root / UNDERSTAND_OUTPUT_DIR
    enforcement_scope = _resolve_enforcement_scope()
    warnings: list[str] = []

    del depth_level  # Compatibility option
    del no_readme  # Compatibility option
    del timeout  # Compatibility option

    requested_plugin = (os.environ.get("DEV_STACK_PLUGIN") or plugin).strip().lower()
    if requested_plugin not in ("auto", *SUPPORTED_PLUGIN_EXPERIENCES):
        warnings.append(
            "Unsupported plugin workflow "
            f"'{requested_plugin}'. Supported values: {', '.join(SUPPORTED_PLUGIN_EXPERIENCES)}."
        )

    bootstrap = understand_runner.verify_bootstrap(repo_root)
    if bootstrap.status != "pass":
        missing = ", ".join(bootstrap.missing_files) if bootstrap.missing_files else KNOWLEDGE_GRAPH_FILE
        _emit_error(
            ctx,
            (
                "Required graph artifacts are missing or invalid. "
                f"Expected under {UNDERSTAND_OUTPUT_DIR}/ ({missing})."
            ),
            exit_code=ExitCode.GENERAL_ERROR,
            details={
                "enforcement_scope": enforcement_scope,
                "missing_files": bootstrap.missing_files,
                "output_dir": str(UNDERSTAND_OUTPUT_DIR),
            },
            warnings=warnings,
        )
        raise SystemExit(ExitCode.GENERAL_ERROR)

    try:
        report = graph_policy.evaluate_repository_graph_freshness(
            repo_root,
            enforcement_scope=enforcement_scope,
            staged=enforcement_scope == "pre_commit",
        )
    except VisualizationError as exc:
        _emit_error(
            ctx,
            str(exc),
            exit_code=ExitCode.GENERAL_ERROR,
            details={"enforcement_scope": enforcement_scope},
            warnings=warnings,
        )
        raise SystemExit(ExitCode.GENERAL_ERROR)

    if incremental and not report.changed_paths:
        payload = {
            "status": "success",
            "skipped": True,
            "reason": "No changed paths detected for freshness evaluation.",
            "incremental": True,
            "enforcement_scope": enforcement_scope,
            "output_dir": str(UNDERSTAND_OUTPUT_DIR),
            "warnings": warnings,
        }
        if ctx.json_output:
            click.echo(json.dumps(payload))
        else:
            click.echo("Graph freshness check skipped: no changed paths detected.")
            for warning in warnings:
                click.echo(f"Warning: {warning}")
        return

    payload = {
        "status": "pass" if not report.outcome.blocked else report.outcome.status,
        "enforcement_scope": enforcement_scope,
        "freshness_state": report.outcome.freshness_state.value,
        "blocked": report.outcome.blocked,
        "incremental": incremental,
        "skipped": False,
        "output_dir": str(UNDERSTAND_OUTPUT_DIR),
        "changed_paths": report.changed_paths,
        "graph_updated_in_change_set": report.graph_updated_in_change_set,
        "detection_mode": report.impact_evaluation.detection_mode,
        "is_graph_impacting": report.impact_evaluation.is_graph_impacting,
        "matched_paths": report.impact_evaluation.matched_paths,
        "unmapped_source_paths": report.impact_evaluation.unmapped_source_paths,
        "storage_violations": report.storage_policy.violations,
        "oversized_json_files": report.storage_policy.oversized_json_files,
        "project": {
            "name": report.bundle.project_name,
            "analyzedAt": report.bundle.analyzed_at,
            "gitCommitHash": report.bundle.git_commit_hash,
        },
        "warnings": warnings,
    }

    if report.outcome.blocked:
        _emit_error(
            ctx,
            report.impact_evaluation.reason,
            exit_code=ExitCode.GENERAL_ERROR,
            details={
                **payload,
                "status": report.outcome.status,
                "remediation_steps": report.outcome.remediation_steps,
                "diagnostics": report.outcome.diagnostics,
            },
            warnings=warnings,
        )
        raise SystemExit(ExitCode.GENERAL_ERROR)

    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        click.echo("Graph freshness validation passed.")
        click.echo(f"  Scope: {enforcement_scope}")
        click.echo(f"  Detection mode: {report.impact_evaluation.detection_mode}")
        click.echo(f"  Graph impacting: {report.impact_evaluation.is_graph_impacting}")
        click.echo(f"  Project: {report.bundle.project_name or 'unknown'}")
        click.echo(f"  Graph analyzedAt: {report.bundle.analyzed_at or 'unknown'}")
        click.echo(f"  Graph gitCommitHash: {report.bundle.git_commit_hash or 'unknown'}")
        if report.storage_policy.oversized_json_files:
            click.echo("  Oversized graph JSON files:")
            for path in report.storage_policy.oversized_json_files:
                click.echo(f"    - {path}")
        for warning in warnings:
            click.echo(f"  Warning: {warning}")


def _resolve_enforcement_scope() -> str:
    raw = os.environ.get("DEV_STACK_GRAPH_SCOPE", "pre_commit").strip().lower()
    if raw in {"pre_commit", "ci_required_check"}:
        return raw
    logger.warning("Unknown DEV_STACK_GRAPH_SCOPE=%r, defaulting to pre_commit", raw)
    return "pre_commit"


def _emit_error(
    ctx: CLIContext,
    message: str,
    *,
    exit_code: int = 1,
    details: dict[str, object] | None = None,
    warnings: list[str] | None = None,
) -> None:
    if ctx.json_output:
        payload: dict[str, object] = {
            "status": "error",
            "message": message,
            "exit_code": exit_code,
        }
        if details:
            for key, value in details.items():
                if key in {"status", "message", "exit_code"}:
                    continue
                payload[key] = value
        if warnings:
            payload["warnings"] = warnings
        click.echo(json.dumps(payload))
    else:
        click.echo(f"Error: {message}", err=True)
