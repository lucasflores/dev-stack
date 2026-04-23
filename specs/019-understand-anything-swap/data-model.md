# Data Model: Replace Codeboarding With Understand-Anything

**Feature**: `019-understand-anything-swap`  
**Date**: 2026-04-22

## Entities

### GraphArtifactBundle

Represents committed Understand-Anything graph assets tracked by dev-stack policy.

| Field | Type | Description |
|-------|------|-------------|
| `graph_dir` | `Path` | Root artifact directory (`.understand-anything/`) |
| `knowledge_graph_path` | `Path` | Path to `knowledge-graph.json` |
| `project_name` | `str` | `project.name` from graph metadata |
| `analyzed_at` | `str` | `project.analyzedAt` timestamp |
| `git_commit_hash` | `str` | `project.gitCommitHash` from graph metadata |
| `node_file_paths` | `set[str]` | Distinct `filePath` values extracted from graph nodes |
| `tracked_json_files` | `list[Path]` | Committed graph JSON files under `.understand-anything/` |

**Validation rules**:
- `knowledge_graph_path` must exist and parse as valid JSON object.
- Graph metadata must include `project` and `nodes` keys.
- `node_file_paths` must be deterministic (sorted before serialization/comparison).

---

### GraphImpactEvaluation

Captures whether current changes require graph artifact refresh.

| Field | Type | Description |
|-------|------|-------------|
| `changed_paths` | `list[str]` | Candidate changed paths (staged or PR diff) |
| `detection_mode` | `str` | `diff_overlay`, `graph_path_intersection`, or `indeterminate` |
| `matched_paths` | `list[str]` | Changed paths found in graph node file set |
| `unmapped_source_paths` | `list[str]` | Source-like paths not represented in graph nodes |
| `is_graph_impacting` | `bool` | True when graph refresh is required |
| `reason` | `str` | Human-actionable explanation |

**Validation rules**:
- If `detection_mode == indeterminate`, enforcement must fail closed.
- `is_graph_impacting` must be true when any `matched_paths` exist.
- New or removed source-like files without graph coverage are treated as impacting.

---

### GraphFreshnessState (Enum)

| Value | Description |
|-------|-------------|
| `MISSING` | Required graph artifacts are absent |
| `CURRENT` | Graph artifacts satisfy freshness policy for current change set |
| `STALE` | Graph-impacting change detected without synchronized graph update |
| `INDETERMINATE` | Detection failed or produced ambiguous result |

**State transitions**:
- `MISSING -> CURRENT`: initial graph generated and committed.
- `CURRENT -> STALE`: graph-impacting code changes occur without graph update.
- `STALE -> CURRENT`: iterative refresh performed and committed.
- `ANY -> INDETERMINATE`: graph parse/detection/storage policy check fails.

---

### GraphStoragePolicy

Defines repository storage rules for committed graph artifacts.

| Field | Type | Description |
|-------|------|-------------|
| `max_inline_json_bytes` | `int` | Threshold for regular Git storage (10 MB) |
| `requires_lfs` | `bool` | True when any committed graph JSON exceeds threshold |
| `gitattributes_entry_present` | `bool` | Whether LFS tracking entry exists for `.understand-anything/*.json` |
| `violations` | `list[str]` | Policy failures requiring blocking output |

**Validation rules**:
- If `requires_lfs` is true, `gitattributes_entry_present` must be true.
- Policy violations block local commit and CI validation.

---

### EnforcementOutcome

Represents blocking behavior for local hooks and CI checks.

| Field | Type | Description |
|-------|------|-------------|
| `scope` | `str` | `pre_commit` or `ci_required_check` |
| `status` | `str` | `pass`, `fail`, or `indeterminate` |
| `blocked` | `bool` | Whether integration is blocked |
| `remediation_steps` | `list[str]` | Ordered instructions for contributor recovery |
| `diagnostics` | `dict[str, object]` | Structured details for JSON output |

**Validation rules**:
- `blocked` must be true for `fail` and `indeterminate` statuses.
- `remediation_steps` must be non-empty when blocked.

## Relationships

- `GraphArtifactBundle` feeds `GraphImpactEvaluation` and `GraphStoragePolicy`.
- `GraphImpactEvaluation` and `GraphStoragePolicy` jointly determine `GraphFreshnessState`.
- `GraphFreshnessState` maps to `EnforcementOutcome` for local and CI scopes.
