# Implementation Plan: Dev-Stack Update Workflow Bug Fixes

**Branch**: `021-update-workflow-bugs` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/021-update-workflow-bugs/spec.md`

## Summary

Fix four bugs encountered when updating dev-stack in a live project: (1) declare `packaging` as a required dependency; (2) replace per-module `VERSION` constants with `importlib.metadata` runtime derivation so a package version bump always surfaces outdated modules; (3) suppress the "missing tools" advisory when core stages were skipped only by `--stage` filtering; (4) add `as_of` and `stale` fields to the persisted pipeline run record so developers and agents can assess data freshness programmatically.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: `click`, `rich`, `importlib.metadata` (stdlib), `packaging>=24.0` (new declared dep)  
**Storage**: `.dev-stack/pipeline/last-run.json` (JSON file), `dev-stack.toml` (TOML manifest)  
**Testing**: pytest (`uv run pytest`)  
**Target Platform**: macOS / Linux CLI  
**Project Type**: Single Python package (`src/dev_stack/`)  
**Performance Goals**: N/A — correctness fixes, not performance changes  
**Constraints**: Backward-compatible JSON output (no fields removed); no new runtime deps beyond `packaging`  
**Scale/Scope**: 4 surgical fixes across 3 subsystems (package metadata, pipeline runner, module registry)

## Constitution Check

*GATE: Passed before Phase 0. Re-checked after Phase 1.*

| Principle | Status | Notes |
|---|---|---|
| I. CLI-First Interface | PASS | All fixes are in CLI command paths; JSON output extended, not broken |
| II. Spec-Driven Development | PASS | spec.md exists and is complete before any implementation |
| III. Automation by Default | PASS | Bug 2 fix removes a manual step (VERSION bump); no new manual steps introduced |
| IV. Brownfield Safety | PASS | No manifest or user files overwritten; JSON output is additive |
| V. AI-Native Architecture | PASS | `stale`/`as_of` fields explicitly serve agent consumers |
| VI. Local-First Execution | PASS | All fixes are in local CLI execution paths |
| VII. Observability & Documentation | PASS | `as_of`/`stale` improve pipeline observability |
| VIII. Modularity & Composability | PASS | Each fix is isolated to its subsystem; no cross-module coupling introduced |

No violations. No Complexity Tracking table required.

## Project Structure

### Documentation (this feature)

```text
specs/021-update-workflow-bugs/
├── plan.md              ← this file
├── research.md          ← Phase 0 complete
├── data-model.md        ← Phase 1 complete
├── quickstart.md        ← Phase 1 complete
├── contracts/
│   └── cli-contracts.md ← Phase 1 complete
└── tasks.md             ← Phase 2 (next: /speckit.tasks)
```

### Source Code (changes only)

```text
pyproject.toml                                  ← Bug 1: add packaging dep

src/dev_stack/modules/__init__.py               ← Bug 2: _package_version(), latest_module_entries()
src/dev_stack/modules/base.py                   ← Bug 2: version property on ModuleBase
src/dev_stack/modules/apm.py                    ← Bug 2: remove VERSION constant
src/dev_stack/modules/ci_workflows.py           ← Bug 2: remove VERSION constant
src/dev_stack/modules/docker.py                 ← Bug 2: remove VERSION constant
src/dev_stack/modules/hooks.py                  ← Bug 2: remove VERSION constant
src/dev_stack/modules/sphinx_docs.py            ← Bug 2: remove VERSION constant
src/dev_stack/modules/uv_project.py             ← Bug 2: remove VERSION constant
src/dev_stack/modules/visualization.py          ← Bug 2: remove VERSION constant

src/dev_stack/pipeline/runner.py                ← Bug 3: hollow-pipeline guard condition
                                                   Bug 4: _record_pipeline_run() + as_of/stale fields

tests/unit/test_module_version.py               ← new: Bug 2 unit tests
tests/unit/test_pipeline_runner.py              ← extend: Bug 3 & 4 unit tests
```

**Structure Decision**: Single project, `src/` layout. No new source directories required.

## Phase 0: Research (Complete)

See [research.md](research.md) for full findings. Summary:

| Bug | Root Cause | Fix Location |
|---|---|---|
| 1 | `packaging` imported in `apm.py` but not declared in `pyproject.toml` | `pyproject.toml` |
| 2 | `latest_module_entries()` reads class-level `VERSION` constants, not bumped with package | `modules/__init__.py`, `modules/base.py`, all module files |
| 3 | Hollow-pipeline guard checks `status == SKIP` without examining `skipped_reason` | `pipeline/runner.py` lines 219–226 |
| 4 | `_record_pipeline_run()` writes no staleness signal; `status_cmd.py` passes raw JSON through | `pipeline/runner.py` `_record_pipeline_run()` |

## Phase 1: Design (Complete)

See [data-model.md](data-model.md) and [contracts/cli-contracts.md](contracts/cli-contracts.md).

Key design decisions:

- **Bug 2**: `_package_version()` helper in `modules/__init__.py` → used by `latest_module_entries()` and a new `version` property on `ModuleBase`. Per-module `VERSION` constants removed entirely.
- **Bug 3**: Hollow-pipeline guard gains an inner condition: only emit advisory if at least one core stage has `skipped_reason != "filtered via --stage"`.
- **Bug 4**: `_record_pipeline_run()` computes `stale` (bool) and `as_of` (ISO timestamp) and writes them to `last-run.json`. No change to `status_cmd.py` — new fields flow through automatically since the full dict is passed under `"pipeline"`.

## Implementation Notes

### Bug 2: `self.VERSION` usages to audit after constant removal

Key locations where `VERSION` is read for reporting (must switch to `self.version` property):

- `status_cmd.py` line ~100: `version=getattr(instance, "VERSION", "unknown")` → `instance.version`
- Each module's `verify()` method: `ModuleStatus(version=self.VERSION, ...)` → `self.version`

### Bug 4: `stale` computation

```python
stale = (
    summary.aborted_stage is not None
    or any(r.skipped_reason == "filtered via --stage" for r in summary.results)
)
```

Hook-context-filtered stages are removed from `stage_defs` before the main loop and never appear in `summary.results`, so they do not affect `stale`. This is intentional — hook runs are expected partial executions.

### Test coverage

Constitution Principle III: coverage MUST NOT decrease. Current threshold: `--cov-fail-under=65`.

- `tests/unit/test_module_version.py`: `_package_version()` returns string; `latest_module_entries()` returns package version for all modules; `ModuleBase.version` property works
- `tests/unit/test_pipeline_runner.py` (extend): hollow-pipeline guard with all filter-skipped core stages → no advisory; guard with tool-missing stages → advisory present; `stale=True` after `--stage` run; `stale=False` after full run; `as_of` present in both cases
