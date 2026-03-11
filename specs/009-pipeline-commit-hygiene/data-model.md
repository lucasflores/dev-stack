# Data Model: Pipeline Commit Hygiene

**Feature Branch**: `009-pipeline-commit-hygiene`
**Date**: 2026-03-10

## Entities

### StageResult (modified)

Existing entity in `src/dev_stack/pipeline/stages.py`. Modified to include output path tracking.

| Field | Type | Description |
|-------|------|-------------|
| `stage_name` | `str` | Stage identifier (existing) |
| `status` | `StageStatus` | Outcome: pass, fail, warn, skip (existing) |
| `failure_mode` | `FailureMode` | hard or soft gate (existing) |
| `duration_ms` | `int` | Execution time (existing) |
| `output` | `str` | Human-readable output text (existing) |
| `skipped_reason` | `str \| None` | Why stage was skipped (existing) |
| `output_paths` | `list[Path]` | **NEW** — Files created/modified by this stage for auto-staging |

**Validation rules**:
- `output_paths` defaults to empty list
- Paths must be absolute
- Paths are only populated when stage status is "pass" or "skip" (stages that fail should leave `output_paths` empty)

### StageContext (modified)

Existing entity in `src/dev_stack/pipeline/stages.py`. Modified to carry hook context.

| Field | Type | Description |
|-------|------|-------------|
| `repo_root` | `Path` | Repository root (existing) |
| `manifest` | `StackManifest \| None` | Stack manifest (existing) |
| `force` | `bool` | Force flag (existing) |
| `agent_bridge` | `AgentBridge \| None` | Agent bridge (existing) |
| `completed_results` | `list[StageResult] \| None` | Prior results (existing) |
| `hook_context` | `str \| None` | **NEW** — Hook type if running in hook context (e.g., "pre-commit"), None if standalone |
| `dry_run` | `bool` | **NEW** — Whether this is a dry-run execution (no file mutations) |

### PipelineRunResult (modified)

Existing entity in `src/dev_stack/pipeline/runner.py`. Modified to track auto-staging outcome.

| Field | Type | Description |
|-------|------|-------------|
| `results` | `list[StageResult]` | Per-stage results (existing) |
| `success` | `bool` | Overall success (existing) |
| `aborted_stage` | `str \| None` | Stage that caused abort (existing) |
| `skip_flag_detected` | `bool` | Skip marker found (existing) |
| `parallelized` | `bool` | Whether parallel execution was used (existing) |
| `warnings` | `list[str]` | Pipeline-level warnings (existing) |
| `auto_staged_paths` | `list[str]` | **NEW** — Paths that were auto-staged during pre-commit |

### LLM API Key Constants

New constant in `src/dev_stack/pipeline/stages.py`.

```python
LLM_API_KEY_VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
)
```

## Relationships

```
PipelineRunner
  ├── creates → StageContext (with hook_context from env)
  ├── executes → PipelineStage[].executor(StageContext) → StageResult[]
  ├── collects → StageResult.output_paths (from pass/skip stages)
  └── runs → _auto_stage_outputs(collected_paths) if hook_context == "pre-commit"
```

## State Transitions

### Security Stage Baseline Workflow

```
[baseline exists?]
    ├── No → skip detect-secrets (pass)
    └── Yes → read existing results
              → run detect-secrets scan --baseline
              → read new results
              → [findings changed?]
                  ├── No → restore original file (no disk change)
                  └── Yes → keep new file, add to output_paths
```

### Visualize Stage Skip Logic

```
[enabled in config?]
    ├── No → skip (config disabled)
    └── Yes → [module installed?]
                ├── No → skip (module not installed)
                └── Yes → [CLI available?]
                            ├── No → skip (install CodeBoarding)
                            └── Yes → [any LLM API key set?]  ← NEW
                                        ├── No → skip (list 5 key names)
                                        └── Yes → run CodeBoarding
```

### Commit-Message Stage Status Logic

```
[agent available?]
    ├── No → skip (agent unavailable)
    └── Yes → [template exists?]
                ├── No → skip (template missing)
                └── Yes → [COMMIT_EDITMSG already has user content?]  ← NEW
                            ├── Yes → skip ("User-supplied message via -m; skipping generated message")
                            └── No → [staged changes exist?]
                                      ├── No → skip (no changes)
                                      └── Yes → invoke agent → write message → pass
```
