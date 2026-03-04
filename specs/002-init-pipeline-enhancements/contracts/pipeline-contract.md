# Pipeline Contract: 8-Stage Pipeline

**Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28

---

## Overview

The pre-commit pipeline expands from 6 to 8 stages. This contract defines the new stage definitions, executor signatures, and behavioral guarantees. The `PipelineStage` dataclass, `StageResult`, `StageContext`, `FailureMode`, and `StageStatus` types are unchanged.

---

## Pipeline Stage Definitions

### build_pipeline_stages() -> list[PipelineStage]

Returns exactly 8 stages in this fixed order:

| Order | Name | Failure Mode | Requires Agent | Executor | Description |
|-------|------|-------------|----------------|----------|-------------|
| 1 | `lint` | HARD | no | `_execute_lint_stage` | ruff format --check + ruff check |
| 2 | `typecheck` | HARD | no | `_execute_typecheck_stage` | mypy type checking (**NEW**) |
| 3 | `test` | HARD | no | `_execute_test_stage` | pytest execution |
| 4 | `security` | HARD | no | `_execute_security_stage` | pip-audit + detect-secrets |
| 5 | `docs-api` | HARD | no | `_execute_docs_api_stage` | Sphinx apidoc + build (**NEW**) |
| 6 | `docs-narrative` | SOFT | yes | `_execute_docs_narrative_stage` | Agent narrative docs (**RENAMED**) |
| 7 | `infra-sync` | SOFT | no | `_execute_infra_sync_stage` | Hash comparison of managed files |
| 8 | `commit-message` | SOFT | yes | `_execute_commit_stage` | Agent commit message generation |

### Stage ordering invariants

- Hard gates (1-5) execute before soft gates (6-8)
- Hard gate failure stops the pipeline; soft gate failure produces a warning
- Stages 6 and 8 require an agent; they SKIP (not FAIL) when agent is unavailable
- Stages 2 and 5 SKIP (not FAIL) when their tool is not installed

---

## New Executor Contracts

### _execute_typecheck_stage(context: StageContext) -> StageResult

**Purpose**: Run mypy type checking against the project source.

**Preconditions**: `StageContext.repo_root` is valid.

**Behavior**:
1. Check `shutil.which("mypy")`:
   - If not found: return `StageResult(status=SKIP, skipped_reason="mypy not found, skipping type check")`
2. Run `python3 -m mypy src/` via `_run_command()`
3. Return PASS if exit code 0, FAIL if exit code 1 (type errors), FAIL if exit code 2 (fatal)

**Return schema**:
```python
# Success
StageResult(stage_name="typecheck", status=StageStatus.PASS,
            failure_mode=FailureMode.HARD, duration_ms=..., output="Success: ...")

# Type errors found
StageResult(stage_name="typecheck", status=StageStatus.FAIL,
            failure_mode=FailureMode.HARD, duration_ms=...,
            output="src/pkg/mod.py:10: error: ...")

# mypy not installed
StageResult(stage_name="typecheck", status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD, duration_ms=...,
            skipped_reason="mypy not found, skipping type check")
```

**Guarantees**:
- Never raises exceptions — all errors caught and returned as StageResult
- Duration is always measured (even for SKIP)
- Uses `_run_command()` helper (same pattern as lint/test/security stages)

---

### _execute_docs_api_stage(context: StageContext) -> StageResult

**Purpose**: Run Sphinx apidoc + build for deterministic API documentation.

**Preconditions**: `StageContext.repo_root` is valid.

**Behavior**:
1. Check Sphinx availability:
   - `shutil.which("sphinx-build")` OR try `importlib.util.find_spec("sphinx")`
   - If not found: return `StageResult(status=SKIP, skipped_reason="sphinx not found, skipping API docs")`
2. Detect package name from `src/` directory (first subdirectory that is a Python package)
3. Run `python3 -m sphinx.ext.apidoc -o docs/api src/{pkg} -f --module-first -e`
4. Run `python3 -m sphinx docs docs/_build -W --keep-going -b html`
5. Return PASS if both commands succeed, FAIL if sphinx-build returns non-zero

**Return schema**:
```python
# Success
StageResult(stage_name="docs-api", status=StageStatus.PASS,
            failure_mode=FailureMode.HARD, duration_ms=...,
            output="build succeeded, ...")

# Sphinx warnings/errors
StageResult(stage_name="docs-api", status=StageStatus.FAIL,
            failure_mode=FailureMode.HARD, duration_ms=...,
            output="WARNING: ...\n")

# Sphinx not installed
StageResult(stage_name="docs-api", status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD, duration_ms=...,
            skipped_reason="sphinx not found, skipping API docs")

# No source packages found (empty src/)
StageResult(stage_name="docs-api", status=StageStatus.PASS,
            failure_mode=FailureMode.HARD, duration_ms=...,
            output="No Python packages found in src/, nothing to document")
```

**Guarantees**:
- Deterministic: same source → same docs output (binary-identical with `-f` flag)
- `-W` flag ensures Sphinx warnings become errors
- `--keep-going` reports ALL errors, not just the first
- Uses `python3 -m` invocation, not CLI binaries (avoids PATH issues in venvs)

---

### _execute_docs_narrative_stage(context: StageContext) -> StageResult

**Purpose**: Invoke the coding agent to produce or update narrative documentation.

**Preconditions**: `StageContext.agent_bridge` may or may not be available.

**Behavior**:
1. If `context.agent_bridge` is None: return `StageResult(status=SKIP, skipped_reason="no agent configured")`
2. Read narrative prompt template from `templates/prompts/docs_update.txt`
3. Invoke agent via `AgentBridge` with prompt scoped to `docs/guides/`
4. Return PASS if agent succeeds, WARN if agent fails (soft gate)

**Differences from old `_execute_docs_stage`**:
- Writes to `docs/guides/` (not generic docs path)
- Prompt explicitly excludes API reference material
- Stage name is `"docs-narrative"` (not `"docs"`)

---

## Shared Helper Contract

### _detect_src_package(repo_root: Path) -> str | None

**Purpose**: Find the Python package name under `src/`.

**Behavior**:
1. Scan `repo_root / "src"` for subdirectories containing `__init__.py`
2. Return the first match (sorted alphabetically for determinism)
3. Return `None` if no package found

This helper is used by both `_execute_docs_api_stage` and `_execute_typecheck_stage`.

---

## Updated Prompt Template Contract

### templates/prompts/docs_update.txt

**Previous scope**: Generic documentation updates (API + narrative mixed).

**New scope**: Narrative-only documentation in `docs/guides/`.

**Required directives** in the updated template:
1. "Generate or update narrative documentation in `docs/guides/`"
2. "Focus on: tutorials, quickstarts, architecture walkthroughs, capability guides"
3. "Do NOT generate API reference documentation — API docs are handled by the deterministic docs-api stage via Sphinx"
4. "If `docs/guides/` does not exist, create it"

---

## Pre-commit Hook Template Contract

### templates/hooks/pre-commit-config.yaml

**Addition**: mypy hook entry appended to the existing local hooks:

```yaml
- repo: local
  hooks:
    # ... existing hooks (ruff, pytest, etc.) ...
    - id: mypy
      name: mypy type check
      entry: python3 -m mypy src/
      language: system
      pass_filenames: false
      types: [python]
```

**Guarantees**:
- Uses `repo: local` (consistent with all existing hooks)
- Uses `python3 -m mypy` (not `mypy` binary — avoids PATH issues)
- `pass_filenames: false` ensures mypy checks entire `src/` directory, not individual files
- `types: [python]` ensures hook only triggers for Python file changes

---

## Pipeline JSON Output Contract

When `--json` is used, the pipeline output schema includes all 8 stages:

```json
{
  "pipeline": {
    "stages": [
      {"name": "lint", "order": 1, "status": "pass", "failure_mode": "hard", "duration_ms": 1200},
      {"name": "typecheck", "order": 2, "status": "pass", "failure_mode": "hard", "duration_ms": 3500},
      {"name": "test", "order": 3, "status": "pass", "failure_mode": "hard", "duration_ms": 8200},
      {"name": "security", "order": 4, "status": "pass", "failure_mode": "hard", "duration_ms": 2100},
      {"name": "docs-api", "order": 5, "status": "pass", "failure_mode": "hard", "duration_ms": 4500},
      {"name": "docs-narrative", "order": 6, "status": "skip", "failure_mode": "soft", "duration_ms": 10},
      {"name": "infra-sync", "order": 7, "status": "pass", "failure_mode": "soft", "duration_ms": 300},
      {"name": "commit-message", "order": 8, "status": "pass", "failure_mode": "soft", "duration_ms": 5000}
    ],
    "total_stages": 8,
    "passed": 6,
    "failed": 0,
    "skipped": 1,
    "warned": 0,
    "hard_gate_passed": true
  }
}
```

---

## Test Implications

### Tests that MUST be updated

| Test file | Change required |
|-----------|----------------|
| `tests/unit/test_pipeline_stages.py` | Assert 8 stages (was 6). Verify order, names, failure modes. |
| `tests/unit/test_modules_registry.py` | Assert `DEFAULT_GREENFIELD_MODULES` = `("uv_project", "sphinx_docs", "hooks", "speckit")` |
| `tests/contract/test_cli_json_output.py` | Assert `total_stages: 8` in JSON output |
| `tests/contract/test_module_interface.py` | Verify `uv_project` and `sphinx_docs` satisfy `ModuleBase` contract |
| `tests/integration/test_init_greenfield.py` | Verify UV + Sphinx artifacts in greenfield output |
| `tests/integration/test_init_brownfield.py` | Verify conflict flow for new files |

### New test files

| Test file | Purpose |
|-----------|---------|
| `tests/unit/test_uv_project.py` | Unit tests for UvProjectModule |
| `tests/unit/test_sphinx_docs.py` | Unit tests for SphinxDocsModule |
