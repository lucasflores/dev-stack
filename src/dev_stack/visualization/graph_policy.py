"""Graph freshness policy helpers for Understand-Anything artifacts."""
from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..errors import VisualizationError
from .understand_runner import (
    DIFF_OVERLAY_FILE,
    GraphMetadata,
    INTERMEDIATE_DIR,
    KNOWLEDGE_GRAPH_FILE,
    UNDERSTAND_OUTPUT_DIR,
    extract_graph_metadata,
    list_committed_graph_json,
    load_knowledge_graph,
)


SOURCE_FILE_GLOBS: tuple[str, ...] = ("src/**", "tests/**", "scripts/**")
MAX_INLINE_JSON_BYTES = 10 * 1024 * 1024
LEGACY_REFERENCE_PATTERNS: tuple[str, ...] = ("codeboarding", ".codeboarding")
GUARDRAIL_PATHS: tuple[Path, ...] = (
    Path("README.md"),
    Path("README.md.bak"),
    Path("src/dev_stack/cli/visualize_cmd.py"),
    Path("src/dev_stack/modules/visualization.py"),
    Path("src/dev_stack/pipeline/stages.py"),
    Path("src/dev_stack/modules/uv_project.py"),
    Path("src/dev_stack/templates/ci/dev-stack-tests.yml"),
)


class GraphFreshnessState(str, Enum):
    MISSING = "MISSING"
    CURRENT = "CURRENT"
    STALE = "STALE"
    INDETERMINATE = "INDETERMINATE"


@dataclass(slots=True)
class GraphArtifactBundle:
    graph_dir: Path
    knowledge_graph_path: Path
    project_name: str | None
    analyzed_at: str | None
    git_commit_hash: str | None
    node_file_paths: set[str]
    tracked_json_files: list[Path]


@dataclass(slots=True)
class GraphImpactEvaluation:
    changed_paths: list[str]
    detection_mode: str
    matched_paths: list[str]
    unmapped_source_paths: list[str]
    is_graph_impacting: bool
    reason: str

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "detectionMode": self.detection_mode,
            "isGraphImpacting": self.is_graph_impacting,
            "matchedPaths": self.matched_paths,
            "unmappedSourcePaths": self.unmapped_source_paths,
            "reason": self.reason,
        }


@dataclass(slots=True)
class GraphStoragePolicy:
    max_inline_json_bytes: int
    oversized_json_files: list[str]
    gitattributes_has_lfs_rule: bool
    violations: list[str] = field(default_factory=list)

    @property
    def requires_lfs(self) -> bool:
        return bool(self.oversized_json_files)


@dataclass(slots=True)
class EnforcementOutcome:
    scope: str
    status: str
    blocked: bool
    freshness_state: GraphFreshnessState
    remediation_steps: list[str]
    diagnostics: dict[str, object]


@dataclass(slots=True)
class GraphFreshnessReport:
    bundle: GraphArtifactBundle
    impact_evaluation: GraphImpactEvaluation
    storage_policy: GraphStoragePolicy
    outcome: EnforcementOutcome
    changed_paths: list[str]
    graph_updated_in_change_set: bool


def _normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def is_graph_artifact_path(path: str) -> bool:
    normalized = _normalize(path)
    if not normalized.startswith(f"{UNDERSTAND_OUTPUT_DIR.as_posix()}/"):
        return False
    rel = normalized[len(UNDERSTAND_OUTPUT_DIR.as_posix()) + 1 :]
    if rel == DIFF_OVERLAY_FILE:
        return False
    if rel.startswith(f"{INTERMEDIATE_DIR}/"):
        return False
    return True


def _is_source_like(path: str, source_file_globs: tuple[str, ...]) -> bool:
    normalized = _normalize(path)
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in source_file_globs)


def collect_changed_paths(repo_root: Path, *, staged: bool) -> list[str]:
    """Collect changed paths for local hooks or CI checks."""

    if staged:
        commands = [["git", "diff", "--name-only", "--cached"]]
    else:
        commands = [
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            ["git", "diff", "--name-only", "HEAD"],
        ]

    for command in commands:
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue

        if completed.returncode != 0:
            continue

        paths = sorted({_normalize(line) for line in completed.stdout.splitlines() if line.strip()})
        return paths

    return []


def has_graph_updates(changed_paths: list[str]) -> bool:
    """Return True when changed paths include committed graph artifacts."""

    return any(is_graph_artifact_path(path) for path in changed_paths)


def build_graph_artifact_bundle(repo_root: Path) -> GraphArtifactBundle:
    graph_payload = load_knowledge_graph(repo_root)
    metadata: GraphMetadata = extract_graph_metadata(graph_payload)

    graph_dir = repo_root / UNDERSTAND_OUTPUT_DIR
    knowledge_graph_path = graph_dir / KNOWLEDGE_GRAPH_FILE
    tracked_json_files = list_committed_graph_json(repo_root)

    return GraphArtifactBundle(
        graph_dir=graph_dir,
        knowledge_graph_path=knowledge_graph_path,
        project_name=metadata.project_name,
        analyzed_at=metadata.analyzed_at,
        git_commit_hash=metadata.git_commit_hash,
        node_file_paths=metadata.node_file_paths,
        tracked_json_files=tracked_json_files,
    )


def evaluate_graph_impact(
    *,
    changed_paths: list[str],
    graph_node_file_paths: set[str],
    diff_overlay_present: bool,
    source_file_globs: tuple[str, ...] = SOURCE_FILE_GLOBS,
) -> GraphImpactEvaluation:
    """Evaluate graph impact using ordered detection rules."""

    normalized_changed = sorted({_normalize(path) for path in changed_paths if path.strip()})
    normalized_nodes = {_normalize(path) for path in graph_node_file_paths}

    if not normalized_changed:
        return GraphImpactEvaluation(
            changed_paths=[],
            detection_mode="graph_path_intersection",
            matched_paths=[],
            unmapped_source_paths=[],
            is_graph_impacting=False,
            reason="No changed paths detected.",
        )

    if diff_overlay_present:
        impacting = any(_is_source_like(path, source_file_globs) for path in normalized_changed)
        return GraphImpactEvaluation(
            changed_paths=normalized_changed,
            detection_mode="diff_overlay",
            matched_paths=[],
            unmapped_source_paths=[],
            is_graph_impacting=impacting,
            reason="Diff overlay detected; source changes require graph synchronization." if impacting else "Diff overlay detected but no source-like changes found.",
        )

    if not normalized_nodes and any(_is_source_like(path, source_file_globs) for path in normalized_changed):
        return GraphImpactEvaluation(
            changed_paths=normalized_changed,
            detection_mode="indeterminate",
            matched_paths=[],
            unmapped_source_paths=normalized_changed,
            is_graph_impacting=True,
            reason="Graph node coverage is unavailable; fail closed as indeterminate.",
        )

    matched = sorted(path for path in normalized_changed if path in normalized_nodes)
    unmapped = sorted(
        path
        for path in normalized_changed
        if _is_source_like(path, source_file_globs)
        and path not in normalized_nodes
        and not is_graph_artifact_path(path)
    )

    if matched or unmapped:
        reason = "Matched source paths were found in committed graph coverage."
        if unmapped and not matched:
            reason = "Source-like paths are not represented in graph nodes; treat as graph-impacting."
        return GraphImpactEvaluation(
            changed_paths=normalized_changed,
            detection_mode="graph_path_intersection",
            matched_paths=matched,
            unmapped_source_paths=unmapped,
            is_graph_impacting=True,
            reason=reason,
        )

    return GraphImpactEvaluation(
        changed_paths=normalized_changed,
        detection_mode="graph_path_intersection",
        matched_paths=[],
        unmapped_source_paths=[],
        is_graph_impacting=False,
        reason="No graph-impacting source paths detected.",
    )


def _has_lfs_rule(repo_root: Path) -> bool:
    gitattributes = repo_root / ".gitattributes"
    if not gitattributes.exists():
        return False
    content = gitattributes.read_text(encoding="utf-8")
    return ".understand-anything/*.json" in content and "filter=lfs" in content


def evaluate_storage_policy(
    repo_root: Path,
    *,
    max_inline_json_bytes: int = MAX_INLINE_JSON_BYTES,
) -> GraphStoragePolicy:
    """Validate repository storage rules for graph JSON artifacts."""

    oversized: list[str] = []
    for path in list_committed_graph_json(repo_root):
        try:
            if path.stat().st_size > max_inline_json_bytes:
                oversized.append(path.relative_to(repo_root).as_posix())
        except OSError as exc:
            raise VisualizationError(f"Failed to inspect graph artifact size for {path}: {exc}") from exc

    has_lfs_rule = _has_lfs_rule(repo_root)
    violations: list[str] = []
    if oversized and not has_lfs_rule:
        violations.append(
            "Large graph JSON artifacts exceed 10 MB but .gitattributes is missing the .understand-anything/*.json LFS rule."
        )

    return GraphStoragePolicy(
        max_inline_json_bytes=max_inline_json_bytes,
        oversized_json_files=oversized,
        gitattributes_has_lfs_rule=has_lfs_rule,
        violations=violations,
    )


def detect_legacy_reference_violations(repo_root: Path) -> list[str]:
    """Return guardrail violations for legacy CodeBoarding references."""

    violations: list[str] = []
    for rel_path in GUARDRAIL_PATHS:
        abs_path = repo_root / rel_path
        if not abs_path.exists() or not abs_path.is_file():
            continue
        try:
            content = abs_path.read_text(encoding="utf-8").lower()
        except OSError:
            continue

        for pattern in LEGACY_REFERENCE_PATTERNS:
            if pattern in content:
                violations.append(f"{rel_path.as_posix()}: contains '{pattern}'")
                break
    return violations


def validate_graph_freshness(
    *,
    enforcement_scope: str,
    impact_evaluation: GraphImpactEvaluation,
    storage_policy: GraphStoragePolicy,
    graph_updated_in_change_set: bool,
    has_knowledge_graph: bool,
) -> EnforcementOutcome:
    """Compute pass/fail/indeterminate freshness outcome."""

    remediation_steps = [
        "Regenerate graph artifacts using the supported Understand-Anything plugin workflow.",
        "Commit .understand-anything/knowledge-graph.json and any related graph updates.",
        "Re-run dev-stack visualize to confirm freshness state is CURRENT.",
    ]

    diagnostics: dict[str, object] = {
        "detectionMode": impact_evaluation.detection_mode,
        "isGraphImpacting": impact_evaluation.is_graph_impacting,
        "matchedPaths": impact_evaluation.matched_paths,
        "unmappedSourcePaths": impact_evaluation.unmapped_source_paths,
        "storageViolations": storage_policy.violations,
        "graphUpdatedInChangeSet": graph_updated_in_change_set,
        "oversizedJsonFiles": storage_policy.oversized_json_files,
    }

    if not has_knowledge_graph:
        return EnforcementOutcome(
            scope=enforcement_scope,
            status="fail",
            blocked=True,
            freshness_state=GraphFreshnessState.MISSING,
            remediation_steps=remediation_steps,
            diagnostics=diagnostics,
        )

    if storage_policy.violations:
        return EnforcementOutcome(
            scope=enforcement_scope,
            status="fail",
            blocked=True,
            freshness_state=GraphFreshnessState.STALE,
            remediation_steps=remediation_steps,
            diagnostics=diagnostics,
        )

    if impact_evaluation.detection_mode == "indeterminate":
        return EnforcementOutcome(
            scope=enforcement_scope,
            status="indeterminate",
            blocked=True,
            freshness_state=GraphFreshnessState.INDETERMINATE,
            remediation_steps=remediation_steps,
            diagnostics=diagnostics,
        )

    if impact_evaluation.is_graph_impacting and not graph_updated_in_change_set:
        return EnforcementOutcome(
            scope=enforcement_scope,
            status="fail",
            blocked=True,
            freshness_state=GraphFreshnessState.STALE,
            remediation_steps=remediation_steps,
            diagnostics=diagnostics,
        )

    return EnforcementOutcome(
        scope=enforcement_scope,
        status="pass",
        blocked=False,
        freshness_state=GraphFreshnessState.CURRENT,
        remediation_steps=[],
        diagnostics=diagnostics,
    )


def evaluate_repository_graph_freshness(
    repo_root: Path,
    *,
    enforcement_scope: str,
    staged: bool,
) -> GraphFreshnessReport:
    """Evaluate current repository graph freshness end-to-end."""

    bundle = build_graph_artifact_bundle(repo_root)
    changed_paths = collect_changed_paths(repo_root, staged=staged)

    diff_overlay_present = (repo_root / UNDERSTAND_OUTPUT_DIR / DIFF_OVERLAY_FILE).exists()
    impact = evaluate_graph_impact(
        changed_paths=changed_paths,
        graph_node_file_paths=bundle.node_file_paths,
        diff_overlay_present=diff_overlay_present,
    )
    storage = evaluate_storage_policy(repo_root)
    updated = has_graph_updates(changed_paths)

    outcome = validate_graph_freshness(
        enforcement_scope=enforcement_scope,
        impact_evaluation=impact,
        storage_policy=storage,
        graph_updated_in_change_set=updated,
        has_knowledge_graph=bundle.knowledge_graph_path.exists(),
    )

    legacy_violations = detect_legacy_reference_violations(repo_root)
    if legacy_violations:
        remediation_steps = [
            "Remove legacy CodeBoarding/.codeboarding references from maintained docs and automation paths.",
            *(
                outcome.remediation_steps
                or [
                    "Regenerate graph artifacts using the supported Understand-Anything plugin workflow.",
                    "Commit .understand-anything/knowledge-graph.json and related graph updates.",
                ]
            ),
        ]
        diagnostics = {
            **outcome.diagnostics,
            "legacyReferenceViolations": legacy_violations,
        }
        outcome = EnforcementOutcome(
            scope=enforcement_scope,
            status="fail",
            blocked=True,
            freshness_state=GraphFreshnessState.STALE,
            remediation_steps=remediation_steps,
            diagnostics=diagnostics,
        )

    return GraphFreshnessReport(
        bundle=bundle,
        impact_evaluation=impact,
        storage_policy=storage,
        outcome=outcome,
        changed_paths=changed_paths,
        graph_updated_in_change_set=updated,
    )
