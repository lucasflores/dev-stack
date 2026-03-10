"""Pipeline CLI command definitions."""
from __future__ import annotations

import json
from pathlib import Path

import click

from ..pipeline.agent_bridge import AgentBridge
from ..pipeline.runner import PipelineRunResult, PipelineRunner
from ..pipeline.stages import StageResult
from ..manifest import StackManifest, read_manifest
from ._constants import MANIFEST_FILENAME
from .main import CLIContext, ExitCode, cli


@cli.group()
@click.pass_obj
def pipeline(ctx: CLIContext) -> None:  # pragma: no cover - declarative click entry point
    """Pipeline commands."""


@pipeline.command("run")
@click.option("--stage", "stage_names", multiple=True, help="Run only specific stage(s).")
@click.option("--force", is_flag=True, help="Allow the commit to proceed despite hard failures.")
@click.pass_obj
def pipeline_run(ctx: CLIContext, stage_names: tuple[str, ...], force: bool) -> None:
    """Execute the pre-commit pipeline."""

    repo_root = Path.cwd()
    manifest = _try_load_manifest(repo_root)
    agent_bridge = AgentBridge(repo_root, manifest=manifest)
    runner = PipelineRunner(repo_root, agent_bridge=agent_bridge)
    try:
        result = runner.run(force=force, stages=stage_names)
    except ValueError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.INVALID_USAGE)

    payload = _serialize_run(result, force)
    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        _emit_human_readable(payload)

    if not result.success:
        raise SystemExit(ExitCode.PIPELINE_FAILURE)


def _emit_error(ctx: CLIContext, message: str) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)


def _serialize_run(result: PipelineRunResult, force: bool) -> dict:
    if result.success:
        status = "success"
    elif force:
        status = "completed_with_failures"
    else:
        status = "failed"
    return {
        "status": status,
        "forced": force,
        "aborted_stage": result.aborted_stage,
        "skip_flag_detected": result.skip_flag_detected,
        "parallelized": result.parallelized,
        "warnings": result.warnings,
        "stages": [_serialize_stage(stage) for stage in result.results],
    }


def _serialize_stage(stage: StageResult) -> dict:
    data = {
        "name": stage.stage_name,
        "status": stage.status.value,
        "failure_mode": stage.failure_mode.value,
        "duration_ms": stage.duration_ms,
    }
    if stage.output:
        data["output"] = stage.output
    if stage.skipped_reason:
        data["skipped_reason"] = stage.skipped_reason
    return data


def _emit_human_readable(payload: dict) -> None:
    status = payload["status"]
    click.echo(f"Pipeline status: {status}")
    for warning in payload.get("warnings", []):
        click.echo(warning, err=True)
    if payload.get("skip_flag_detected"):
        if status == "success":
            click.echo(" - Previous commit skipped the pipeline; flag cleared")
        else:
            click.echo(" - Warning: a previous commit skipped the pipeline; flag still present")
    if payload.get("aborted_stage"):
        click.echo(f" - Aborted at stage: {payload['aborted_stage']}")
    if payload.get("parallelized"):
        click.echo(" - Stages 1-3 executed in parallel")
    for stage in payload["stages"]:
        line = f"[{stage['failure_mode']}] {stage['name']}: {stage['status']}"
        if stage.get("skipped_reason"):
            line += f" (reason: {stage['skipped_reason']})"
        click.echo(line)
        if stage.get("output"):
            click.echo(f"    {stage['output']}")


def _try_load_manifest(repo_root: Path) -> StackManifest | None:
    """Load dev-stack.toml if it exists, returning None on any error."""
    manifest_path = repo_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return read_manifest(manifest_path)
    except Exception:
        return None
