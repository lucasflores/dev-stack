# Data Model: Greenfield Init Fixes

**Feature**: 008-greenfield-init-fixes
**Date**: 2026-03-10

## Entity Modifications

This feature modifies existing entities — no new entities are introduced.

### ModuleResult (existing — no changes)

```
ModuleResult
├── success: bool
├── message: str
├── files_created: list[Path]
└── warnings: list[str]         # FR-009: uv sync failures reported here
```

No schema changes. The `warnings` field already exists and is used for reporting non-fatal issues (e.g., "uv lock failed"). FR-009 adds `uv sync` failure messages to this same field.

### PipelineRunResult (modified)

```
PipelineRunResult
├── results: list[StageResult]
├── success: bool
├── aborted_stage: str | None
├── skip_flag_detected: bool
├── parallelized: bool
└── warnings: list[str]         # NEW — FR-005: hollow pipeline warning
```

**New field**: `warnings: list[str]` with default `[]`. Contains structured warning messages, including the hollow-pipeline banner when all core stages skip.

### StageResult (existing — semantic change only)

```
StageResult
├── stage_name: str
├── status: StageStatus          # pass | fail | warn | skip
├── failure_mode: FailureMode    # hard | soft
├── duration_ms: int
├── output: str
└── skipped_reason: str | None   # FR-004: now includes remediation hint
```

No schema changes. The `skipped_reason` field's **content format** changes from bare tool name to `"{tool} not installed in project venv — run 'uv sync --extra dev' to install"`.

### StageContext (existing — no changes)

```
StageContext
├── repo_root: Path
├── manifest: StackManifest | None  # FR-006: now populated by pipeline_cmd.py
├── force: bool
├── agent_bridge: AgentBridge | None
└── completed_results: list[StageResult] | None
```

The `manifest` field already exists but was always `None` in the pipeline path. FR-006 populates it.

## Data Flow: Greenfield Init (fixed)

```
User runs: dev-stack --json init
  │
  ├── init_cmd.py
  │   ├── detect greenfield via is_greenfield_uv_package()
  │   ├── mark conflicts as "greenfield_predecessor"
  │   ├── set effective_force based on greenfield detection  ← FIX
  │   │
  │   ├── _install_modules(modules, force=effective_force)
  │   │   └── uv_project.install(force=True)               ← NOW RUNS FULLY
  │   │       ├── Step 1: skip uv init (pyproject exists)
  │   │       ├── Step 2: _augment_pyproject()              ← NOW EXECUTES
  │   │       │   └── adds [project.optional-dependencies.dev] and .docs
  │   │       ├── Step 3: _scaffold_tests()                 ← NOW EXECUTES
  │   │       │   └── creates tests/__init__.py, tests/test_placeholder.py
  │   │       ├── Step 4: _run_uv_lock()                   ← NOW EXECUTES
  │   │       └── Step 5: _ensure_standard_gitignore()     ← NOW EXECUTES
  │   │
  │   ├── uv sync --all-extras                              ← NOW INSTALLS DEV TOOLS
  │   ├── write dev-stack.toml (with agent config)
  │   └── emit init result
  │
  └── User runs: git add -A && git commit
      │
      └── pre-commit hook → dev-stack pipeline run
          ├── pipeline_cmd.py loads dev-stack.toml           ← NEW
          ├── AgentBridge(repo_root, manifest=manifest)      ← NEW
          ├── PipelineRunner.run()
          │   ├── lint: ruff found in .venv → PASS           ← FIXED
          │   ├── typecheck: mypy found in .venv → PASS      ← FIXED
          │   ├── test: pytest found in .venv → PASS         ← FIXED
          │   ├── security: pip-audit → PASS
          │   ├── docs-api: sphinx found → PASS              ← FIXED
          │   ├── docs-narrative: agent from manifest → ...  ← FIXED
          │   └── ... remaining stages
          └── emit pipeline result (no hollow warning)
```

## Data Flow: Pipeline with Missing Tools (fallback)

```
Pipeline runs with tools not installed (e.g., uv sync failed):
  │
  ├── Stage: lint
  │   └── _tool_available_in_venv("ruff") → False
  │       └── StageResult(status=SKIP, skipped_reason=
  │           "ruff not installed in project venv — run 'uv sync --extra dev' to install")
  │
  ├── Stage: typecheck
  │   └── skipped_reason="mypy not installed..."
  │
  ├── Stage: test
  │   └── skipped_reason="pytest not installed..."
  │
  └── PipelineRunner post-loop check:
      ├── all core stages (lint, typecheck, test) have SKIP status
      ├── append to warnings: "⚠ No substantive validation: lint, typecheck, test
      │   all skipped due to missing tools. Run 'uv sync --extra dev' to install."
      └── success = True (commit allowed per FR-005)
```

## State Transitions

### uv_project.install() — Decision Tree (fixed)

```
Entry: install(force=bool)
  │
  ├── uv not on PATH? → return failure
  │
  ├── pyproject.toml exists?
  │   ├── NO (true greenfield):
  │   │   └── run uv init → augment → scaffold tests → lock → gitignore
  │   │
  │   ├── YES + force=True (brownfield forced or greenfield predecessor):
  │   │   └── skip uv init → augment → scaffold tests → lock → gitignore  ← FIX
  │   │
  │   └── YES + force=False (brownfield, no force):
  │       └── return failure ("pyproject.toml already exists")
  │
  └── return success with files_created list
```

### Agent Detection — Priority Chain (unchanged logic, fixed wiring)

```
detect_agent(manifest) priority:
  1. DEV_STACK_AGENT env var (if set and non-empty)
  2. manifest.agent config (if manifest provided and agent != "none")
  3. Local binary scan: claude → gh copilot → cursor
  4. Fallback: AgentInfo(cli="none", path=None)
```

The fix: `pipeline_cmd.py` now loads the manifest and passes it to `AgentBridge`, enabling priority #2 to fire.
