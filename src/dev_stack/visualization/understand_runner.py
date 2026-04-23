"""Understand-Anything artifact helpers for visualization workflows."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import VisualizationError

logger = logging.getLogger(__name__)

UNDERSTAND_OUTPUT_DIR = Path(".understand-anything")
KNOWLEDGE_GRAPH_FILE = "knowledge-graph.json"
DIFF_OVERLAY_FILE = "diff-overlay.json"
INTERMEDIATE_DIR = "intermediate"

SUPPORTED_PLUGIN_EXPERIENCES: tuple[str, ...] = ("copilot", "claude")


@dataclass(slots=True)
class RunResult:
    """Result of an optional Understand-Anything subprocess invocation."""

    success: bool
    stdout: str
    stderr: str
    return_code: int


@dataclass(slots=True)
class BootstrapVerifyResult:
    """Status of committed graph bootstrap artifacts."""

    status: str
    has_knowledge_graph: bool
    missing_files: list[str]
    project_name: str | None
    analyzed_at: str | None
    git_commit_hash: str | None


@dataclass(slots=True)
class GraphMetadata:
    """Normalized metadata extracted from knowledge-graph.json."""

    project_name: str | None
    analyzed_at: str | None
    git_commit_hash: str | None
    node_file_paths: set[str]


def _graph_dir(repo_root: Path) -> Path:
    return repo_root / UNDERSTAND_OUTPUT_DIR


def check_cli_available() -> bool:
    """Return True when an Understand-Anything command is present on PATH."""

    return shutil.which("understand-anything") is not None or shutil.which("understand") is not None


def run(
    repo_root: Path,
    depth_level: int = 2,
    *,
    incremental: bool = False,
    timeout: int = 300,
) -> RunResult:
    """Best-effort wrapper for an optional Understand-Anything CLI command.

    This is intentionally defensive because interactive plugin workflows may not
    provide a stable standalone command in every environment.
    """

    cli = shutil.which("understand-anything") or shutil.which("understand")
    if cli is None:
        raise VisualizationError(
            "Understand-Anything CLI is not available on PATH. "
            "Use the supported plugin workflow to generate graph artifacts."
        )

    cmd: list[str] = [cli, "--local", str(repo_root), "--depth-level", str(depth_level)]
    if incremental:
        cmd.append("--incremental")

    logger.debug("Running Understand-Anything: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=repo_root,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode() if exc.stderr else "")
        raise VisualizationError(
            f"Understand-Anything timed out after {timeout}s",
            stderr=stderr,
        ) from exc

    return RunResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )


def load_knowledge_graph(repo_root: Path, *, graph_dir: Path | None = None) -> dict:
    """Load committed `.understand-anything/knowledge-graph.json` as a dict."""

    root = graph_dir if graph_dir is not None else _graph_dir(repo_root)
    graph_path = root / KNOWLEDGE_GRAPH_FILE
    if not graph_path.exists():
        raise VisualizationError(f"Required graph artifact not found: {graph_path}")

    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise VisualizationError(f"Failed to parse {graph_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise VisualizationError(f"Expected JSON object in {graph_path}")
    return payload


def extract_node_file_paths(graph_payload: dict) -> set[str]:
    """Extract normalized node file paths from graph payload."""

    nodes = graph_payload.get("nodes", [])
    if not isinstance(nodes, list):
        return set()

    results: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        candidate = node.get("filePath") or node.get("path") or node.get("reference_file")
        if isinstance(candidate, str) and candidate.strip():
            results.add(candidate.strip().replace("\\", "/"))
    return results


def extract_graph_metadata(graph_payload: dict) -> GraphMetadata:
    """Extract project metadata and node coverage from graph payload."""

    project = graph_payload.get("project", {})
    if not isinstance(project, dict):
        project = {}

    return GraphMetadata(
        project_name=project.get("name") if isinstance(project.get("name"), str) else None,
        analyzed_at=project.get("analyzedAt") if isinstance(project.get("analyzedAt"), str) else None,
        git_commit_hash=project.get("gitCommitHash") if isinstance(project.get("gitCommitHash"), str) else None,
        node_file_paths=extract_node_file_paths(graph_payload),
    )


def verify_bootstrap(repo_root: Path, *, required_files: tuple[str, ...] = (KNOWLEDGE_GRAPH_FILE,)) -> BootstrapVerifyResult:
    """Validate required graph artifacts and expose metadata for callers."""

    graph_dir = _graph_dir(repo_root)
    missing_files = [name for name in required_files if not (graph_dir / name).exists()]
    if missing_files:
        return BootstrapVerifyResult(
            status="fail",
            has_knowledge_graph=False,
            missing_files=missing_files,
            project_name=None,
            analyzed_at=None,
            git_commit_hash=None,
        )

    payload = load_knowledge_graph(repo_root, graph_dir=graph_dir)
    metadata = extract_graph_metadata(payload)
    return BootstrapVerifyResult(
        status="pass",
        has_knowledge_graph=True,
        missing_files=[],
        project_name=metadata.project_name,
        analyzed_at=metadata.analyzed_at,
        git_commit_hash=metadata.git_commit_hash,
    )


def list_committed_graph_json(repo_root: Path) -> list[Path]:
    """Return committed graph JSON files excluding local scratch outputs."""

    graph_dir = _graph_dir(repo_root)
    if not graph_dir.is_dir():
        return []

    files: list[Path] = []
    for path in sorted(graph_dir.rglob("*.json")):
        rel = path.relative_to(graph_dir).as_posix()
        if rel.startswith(f"{INTERMEDIATE_DIR}/"):
            continue
        if rel == DIFF_OVERLAY_FILE:
            continue
        files.append(path)
    return files
