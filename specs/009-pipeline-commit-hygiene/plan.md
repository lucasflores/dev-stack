# Implementation Plan: Pipeline Commit Hygiene

**Branch**: `009-pipeline-commit-hygiene` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-pipeline-commit-hygiene/spec.md`

## Summary

Fix 6 issues discovered during greenfield init testing: (1) auto-stage pipeline-generated files during pre-commit hook execution to prevent index/working-tree mismatches and perpetually dirty state; (2) compare `detect-secrets` scan findings against existing baseline to avoid timestamp-only rewrites; (3) detect missing LLM API keys in the visualize stage and skip gracefully; (4) report honest status in the commit-message stage when `-m` overrides generated messages; (5) update README documentation for soft-gate prerequisites.

## Technical Context

**Language/Version**: Python 3.12 (minimum 3.10+)
**Primary Dependencies**: detect-secrets, sphinx, codeboarding (optional), git CLI
**Storage**: JSON files (`.secrets.baseline`, pipeline state), filesystem (docs, `.codeboarding/`)
**Testing**: pytest (unit + integration + contract)
**Target Platform**: macOS, Linux (local development)
**Project Type**: Single Python package (CLI tool)
**Performance Goals**: N/A (pipeline runs are already bounded by stage timeouts)
**Constraints**: Pre-commit hook must complete without user interaction; auto-staging must not corrupt git index
**Scale/Scope**: ~1000 LOC changed across 3 source files + 1 README

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | **PASS** | No CLI changes; pipeline behavior change is internal |
| II. Spec-Driven Development | **PASS** | This plan is spec-driven (spec.md exists) |
| III. Automation by Default | **PASS** | Core goal: fix automation so it works cleanly on first commit |
| IV. Brownfield Safety | **PASS** | Auto-staging only touches pipeline-generated files, never user files |
| V. AI-Native Architecture | **PASS** | No changes to agent architecture |
| VI. Local-First Execution | **PASS** | All changes are local pre-commit hook behavior |
| VII. Observability & Documentation | **PASS** | README updates improve observability of soft-gate prerequisites |
| VIII. Modularity & Composability | **PASS** | Changes are scoped to pipeline internals; no cross-module coupling |

**Pipeline Rules compliance**:
- Idempotency (III): Baseline comparison ensures running twice produces identical results ✓
- Defined execution order (III): No changes to stage ordering ✓
- Hard/soft gate behavior: Preserved exactly ✓
- Auto-staging respects `.gitignore` (IV): Brownfield safety ✓

**Gate result**: PASS — no violations. Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/009-pipeline-commit-hygiene/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/dev_stack/
├── pipeline/
│   ├── runner.py              # PipelineRunner — add auto-staging post-run step
│   ├── stages.py              # Stage executors — security baseline comparison,
│   │                          #   visualize API key check, commit-message -m detection
│   └── agent_bridge.py        # AgentBridge (read-only for this feature)
├── visualization/
│   └── codeboarding_runner.py # CodeBoarding runner (read-only for this feature)
└── templates/
    └── hooks/
        └── pre-commit         # Hook script — add auto-stage after pipeline run

tests/
├── unit/
│   └── pipeline/              # Unit tests for new behavior
└── integration/               # Integration tests for greenfield flow

README.md                      # Documentation updates (soft-gate prerequisites)
```

**Structure Decision**: Single project layout. All changes are within the existing `src/dev_stack/pipeline/` package, the pre-commit hook template, the README, and test directories.
