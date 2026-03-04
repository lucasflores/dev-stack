"""Visualization CLI."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import click

from ..errors import DependencyError
from ..pipeline.agent_bridge import AgentBridge
from ..visualization.d2_gen import D2Generator
from ..visualization.incremental import ManifestStore
from ..visualization.schema_gen import SchemaGenerationError, SchemaGenerator
from ..visualization.scanner import SourceScanner
from .main import CLIContext, ExitCode, cli

DEFAULT_OUTPUT_DIR = Path("docs/diagrams")
D2_SOURCE_PATH = Path(".dev-stack/viz/overview.d2")
OVERVIEW_NAME = "overview"


@cli.command("visualize")
@click.option("--incremental", is_flag=True, help="Only process changed files.")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT_DIR,
    help="Directory (or file path) for rendered diagrams.",
)
@click.option("--format", "format_", type=click.Choice(["svg", "png"]), default="svg")
@click.option(
    "--agent-timeout",
    type=int,
    default=240,
    show_default=True,
    help="Seconds to wait for the coding agent before falling back to cache.",
)
@click.pass_obj
def visualize(
    ctx: CLIContext, incremental: bool, output: Path, format_: str, agent_timeout: int
) -> None:
    repo_root = Path.cwd()
    scanner = SourceScanner(repo_root)
    scan_result = scanner.scan()

    manifest_store = ManifestStore(repo_root)
    previous_manifest = manifest_store.load_manifest()
    current_manifest = manifest_store.build_manifest(scan_result.snapshots)
    changed_paths = manifest_store.changed_paths(previous_manifest, current_manifest)

    agent_bridge = AgentBridge(repo_root)
    schema_generator = SchemaGenerator(repo_root, agent_bridge, cache_path=manifest_store.schema_path)
    schema_content = None
    used_cache_only = False
    fallback_mode = False
    agent_invocations = 0

    if incremental and not changed_paths:
        cached = manifest_store.load_schema()
        if cached:
            schema_content = cached
            used_cache_only = True

    if schema_content is None:
        try:
            schema_result = schema_generator.generate_overview(
                scan_result.destination, timeout_seconds=agent_timeout
            )
            schema_content = schema_result.content
            agent_invocations = 1
        except SchemaGenerationError as exc:
            if exc.cached_schema:
                schema_content = exc.cached_schema
                fallback_mode = True
            else:
                _emit_error(ctx, str(exc))
                raise SystemExit(ExitCode.AGENT_UNAVAILABLE)

    manifest_store.save_manifest(current_manifest)

    generator = D2Generator(repo_root)
    diagram_dir, render_path, json_path = _resolve_output_paths(repo_root, output, format_)
    highlight_paths = changed_paths if changed_paths else set()
    d2_text = generator.render_overview(schema_content, highlight_paths=highlight_paths)

    d2_source = repo_root / D2_SOURCE_PATH
    d2_source.parent.mkdir(parents=True, exist_ok=True)
    d2_source.write_text(d2_text, encoding="utf-8")

    try:
        _render_d2(d2_source, render_path, format_)
    except DependencyError as exc:
        _emit_error(ctx, str(exc))
        raise SystemExit(ExitCode.GENERAL_ERROR)

    generator.render_json(schema_content, output_path=json_path, highlight_paths=highlight_paths)

    render_rel = _rel_path(render_path, repo_root)
    schema_rel = _rel_path(json_path, repo_root)
    payload = {
        "status": "fallback" if fallback_mode else "success",
        "diagrams": [
            {
                "name": OVERVIEW_NAME,
                "path": render_rel,
                "nodes": len(schema_content.get("nodes", [])),
                "flows": len(schema_content.get("flows", [])),
            }
        ],
        "schema_path": schema_rel,
        "files_scanned": len(scan_result.snapshots),
        "files_changed": len(changed_paths),
        "agent_invocations": agent_invocations,
        "cache_used": used_cache_only or fallback_mode,
        "skipped_files": [_rel_path(path, repo_root) for path in scan_result.skipped],
    }

    if ctx.json_output:
        click.echo(json.dumps(payload))
    else:
        mode = "(fallback) " if fallback_mode else ""
        click.echo(f"{mode}Visualization written to {render_rel}")


def _render_d2(source: Path, output: Path, format_: str) -> None:
    d2_cli = shutil.which("d2")
    if not d2_cli:
        raise DependencyError("Visualization", "D2 CLI not found")
    command = [d2_cli, str(source), str(output)]
    if format_ == "png":
        command.extend(["--format", "png"])
    subprocess.run(command, check=True)


def _emit_error(ctx: CLIContext, message: str) -> None:
    if ctx.json_output:
        click.echo(json.dumps({"status": "error", "message": message}))
    else:
        click.echo(message, err=True)


def _resolve_output_paths(repo_root: Path, requested: Path, format_: str) -> tuple[Path, Path, Path]:
    target = repo_root / requested
    if target.suffix and target.suffix.lstrip(".") in {"svg", "png"}:
        diagram_path = target
        diagram_dir = diagram_path.parent
    else:
        diagram_dir = target
        diagram_path = diagram_dir / f"{OVERVIEW_NAME}.{format_}"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    json_path = diagram_dir / f"{OVERVIEW_NAME}.json"
    return diagram_dir, diagram_path, json_path


def _rel_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
