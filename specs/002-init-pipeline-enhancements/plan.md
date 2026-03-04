# Implementation Plan: Init & Pipeline Enhancements

**Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-init-pipeline-enhancements/spec.md`

## Summary

Add three interconnected enhancements to the dev-stack ecosystem: (1) a `uv_project` module that delegates Python project scaffolding to `uv init --package` and augments the resulting `pyproject.toml` with opinionated tool config, (2) a `sphinx_docs` module that scaffolds Sphinx configuration and splits the current single "docs" pipeline stage into deterministic "docs-api" (hard gate) and agent-driven "docs-narrative" (soft gate), and (3) a "typecheck" pipeline stage running mypy between lint and test. The pipeline expands from 6 to 8 stages. All new files are registered as managed artifacts for drift detection and rollback.

## Technical Context

**Language/Version**: Python 3.11+ (project uses `requires-python = ">=3.11"`)
**Primary Dependencies**: click, tomli-w, rich, pathspec (existing); uv CLI (external, v0.5+), sphinx + sphinx-autodoc-typehints + myst-parser (optional docs), mypy (optional dev)
**Storage**: TOML files (`dev-stack.toml` manifest, `pyproject.toml`); filesystem artifacts
**Testing**: pytest with pytest-cov (≥80% coverage enforced); ruff for linting; pip-audit + detect-secrets for security
**Target Platform**: macOS / Linux developer workstations (CLI tool)
**Project Type**: Single Python package, `src/` layout with setuptools
**Performance Goals**: Greenfield init completes in <30s (SC-001); pipeline stages add <5s each for typecheck and docs-api on typical projects
**Constraints**: Local-first execution; no network calls except `uv lock` (resolves against PyPI); coding agent invocation only for docs-narrative and commit-message stages
**Scale/Scope**: Targets repos with ≤500 source files per existing constitution scaling caps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | CLI-First Interface | ✅ PASS | All new modules are invoked through existing `dev-stack init` / `dev-stack update` CLI commands. No new top-level CLI commands required. JSON output mode preserved. |
| II | Spec-Driven Development | ✅ PASS | This plan is derived from `specs/002-init-pipeline-enhancements/spec.md` with 5 clarifications resolved. |
| III | Automation by Default | ✅ PASS | New stages (typecheck, docs-api, docs-narrative) are additive to the existing pipeline. Pipeline remains idempotent. `uv_project` automates Python project setup that was previously manual. |
| IV | Brownfield Safety | ✅ PASS | `uv_project` implements `preview_files()` and feeds conflicts through `ConflictReport`. Tool-section augmentation uses skip-if-exists semantics. `dev-stack update` prompts interactively for new modules. |
| V | AI-Native Architecture | ✅ PASS | docs-narrative stage continues using `AgentBridge` (coding agent CLI). docs-api stage is deterministic (no agent). No raw LLM API calls introduced. |
| VI | Local-First Execution | ✅ PASS | All new stages execute locally. Sphinx builds locally. `uv init` and `uv lock` run locally. |
| VII | Observability & Documentation | ✅ PASS | Sphinx produces auto-generated API docs. Narrative docs are agent-maintained. All managed files appear in `dev-stack status`. |
| VIII | Modularity & Composability | ✅ PASS | `uv_project` and `sphinx_docs` are independent modules with explicit `DEPENDS_ON`. Each can be installed or removed without breaking other modules. Each has its own test coverage. |

**Pipeline Order Gate** (Constitution §Development Workflow): The constitution defines stages 1–3 as hard gates and 4–6 as generative/soft. The new 8-stage pipeline preserves this pattern: stages 1–5 are hard gates (lint, typecheck, test, security, docs-api), stages 6–8 are soft gates (docs-narrative, infra-sync, commit-message). This is a **justified expansion** — typecheck and docs-api are hard gates because they are deterministic, reproducible, and catch real errors.

**GATE RESULT: PASS** — No violations. Complexity tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-init-pipeline-enhancements/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── module-contract.md
│   └── pipeline-contract.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/dev_stack/
├── modules/
│   ├── __init__.py          # UPDATE: DEFAULT_GREENFIELD_MODULES, register imports
│   ├── base.py              # NO CHANGE (preview_files() already exists)
│   ├── uv_project.py        # NEW: UV Project module
│   ├── sphinx_docs.py       # NEW: Sphinx Docs module
│   ├── hooks.py             # UPDATE: pre-commit-config.yaml template adds mypy hook
│   └── ...                  # Existing modules unchanged
├── pipeline/
│   ├── stages.py            # UPDATE: 6→8 stages, new executors
│   └── ...                  # runner.py, agent_bridge.py unchanged
├── templates/
│   ├── prompts/
│   │   ├── docs_update.txt       # UPDATE: narrative-only instructions
│   │   └── commit_message.txt    # NO CHANGE
│   └── hooks/
│       └── pre-commit-config.yaml  # UPDATE: add mypy hook entry
└── ...

tests/
├── unit/
│   ├── test_uv_project.py        # NEW
│   ├── test_sphinx_docs.py       # NEW
│   ├── test_pipeline_stages.py   # UPDATE: 6→8 stages
│   ├── test_modules_registry.py  # UPDATE: new module defaults
│   └── ...
├── integration/
│   ├── test_init_greenfield.py   # UPDATE: verify UV + Sphinx artifacts
│   ├── test_init_brownfield.py   # UPDATE: test conflict flow for new files
│   └── ...
└── contract/
    ├── test_module_interface.py   # UPDATE: new modules satisfy contract
    └── test_cli_json_output.py    # UPDATE: stage count in JSON output
```

**Structure Decision**: Single project, `src/` layout. The existing structure under `src/dev_stack/` is preserved. Two new module files (`uv_project.py`, `sphinx_docs.py`) are added to `src/dev_stack/modules/`. Two new executor functions are added to `stages.py`. Template files are updated in-place.

## Complexity Tracking

No violations — no complexity tracking needed.

---

## Phase 0: Research

**Status**: ✅ Complete — see [research.md](research.md)

Five research tasks resolved all NEEDS CLARIFICATION items:

| ID | Topic | Decision | Impact |
|----|-------|----------|--------|
| R-1 | `uv init --package` output | Produces pyproject.toml with `uv_build` backend, `src/` layout, `.python-version`. Name normalization follows PEP 503. | FR-001 confirmed. Module must avoid `uv init <path>` (subdirectory trap). |
| R-2 | TOML augmentation | `tomllib` + `tomli_w` (both already available). Skip-if-exists via dict lookup. Comments lost but irrelevant for greenfield. | FR-003 brownfield strategy confirmed. No new dependencies. |
| R-3 | Sphinx apidoc + build | `python3 -m sphinx.ext.apidoc` + `python3 -m sphinx`. `-W --keep-going` for warnings-as-errors. `conf.py` needs `sys.path.insert` for src/ layout. | FR-015, FR-017, FR-019a confirmed. |
| R-4 | mypy invocation | `python3 -m mypy src/` with `[tool.mypy]` config. Local pre-commit hook (matches existing pattern). `shutil.which("mypy")` for detection. | FR-022–FR-026 confirmed. |
| R-5 | `uv lock` behavior | `uv lock` (no flags) re-resolves after optional-dep augmentation. Always writes `uv.lock` at project root. Idempotent. | FR-007 confirmed. |

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete

### Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Data Model | [data-model.md](data-model.md) | UvProjectModule, SphinxDocsModule entities; PyprojectAugmentation schema; 8-stage pipeline definition; managed artifacts registry |
| Module Contract | [contracts/module-contract.md](contracts/module-contract.md) | Interface contracts for `uv_project` and `sphinx_docs` modules: install/uninstall/update/verify/preview_files sequences, templates, error handling |
| Pipeline Contract | [contracts/pipeline-contract.md](contracts/pipeline-contract.md) | 8-stage pipeline definition; `_execute_typecheck_stage` and `_execute_docs_api_stage` executor contracts; prompt template contract; pre-commit hook contract; JSON output schema |
| Quickstart | [quickstart.md](quickstart.md) | Developer onboarding guide: greenfield/brownfield flows, 8-stage pipeline table, project layout, update workflow |

### Key Design Decisions

1. **Build backend**: `uv_build` is now uv's default. The module does NOT override it — users get whatever `uv init` produces.
2. **TOML strategy**: `tomllib` + `tomli_w` only (no `tomlkit`). Skip-if-exists means we never modify existing sections, so comment preservation is irrelevant.
3. **Sphinx invocation**: `python3 -m` (not CLI binaries) — avoids PATH issues in venvs, matches existing `_run_command()` pattern.
4. **mypy hook**: Local `repo: local` hook (not `mirrors-mypy`) — consistent with all existing hooks in the template.
5. **Pipeline gate assignment**: Stages 1-5 are HARD (lint, typecheck, test, security, docs-api) because they are deterministic and reproducible. Stages 6-8 are SOFT (docs-narrative, infra-sync, commit-message) because they are generative or advisory.

---

## Post-Design Constitution Re-Check

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | CLI-First Interface | ✅ PASS | No new CLI commands. All capabilities invoked via existing `init`/`update`/`status`. JSON output schema updated for 8 stages. |
| II | Spec-Driven Development | ✅ PASS | Full spec → research → data model → contracts → quickstart chain complete. |
| III | Automation by Default | ✅ PASS | Two new deterministic stages (typecheck, docs-api) are additive. Pipeline remains idempotent (same source → same results). |
| IV | Brownfield Safety | ✅ PASS | `preview_files()` implemented on both modules. Skip-if-exists semantics for TOML augmentation. Update prompts interactively for new modules. |
| V | AI-Native Architecture | ✅ PASS | docs-narrative uses AgentBridge (not raw API). docs-api is deterministic (no agent). No new LLM API calls. |
| VI | Local-First Execution | ✅ PASS | All stages execute locally. `uv lock` resolves against PyPI (network) but this is inherent to dependency management. |
| VII | Observability & Documentation | ✅ PASS | Sphinx produces auto-generated API docs. Narrative docs are agent-maintained. All managed files in `dev-stack status`. |
| VIII | Modularity & Composability | ✅ PASS | `uv_project` and `sphinx_docs` are independent (with explicit DEPENDS_ON). Each has own tests. Can be installed/removed without breaking others. |

**Pipeline Order Expansion** (Constitution §Development Workflow):

The constitution defines a 6-stage pipeline: lint(1) → test(2) → security(3) → docs(4) → infra-sync(5) → commit-message(6). The design expands this to 8 stages by:
- Inserting `typecheck` between lint and test (stage 2)
- Splitting `docs` into `docs-api` (hard, stage 5) and `docs-narrative` (soft, stage 6)

This is a **justified expansion**, not a violation:
- The constitution says "stages 1-3 hard, 4-6 soft". The new pipeline preserves this pattern semantically: stages 1-5 are deterministic/hard, stages 6-8 are generative/soft.
- `typecheck` is a natural extension of the quality gate chain (lint → typecheck → test).
- `docs-api` is a natural demotion from soft to hard — Sphinx builds are deterministic and should gate.
- A constitution amendment (v1.1.0 MINOR) should update the pipeline definition to 8 stages.

**GATE RESULT: PASS** — No violations. Constitution amendment recommended for pipeline stage count.

---

## Next Steps

This plan is complete through Phase 1. The next step is `/speckit.tasks` to generate the implementation task list (`tasks.md`).

**Implementation order** (from dependency analysis):
1. `uv_project` module (foundation — no deps)
2. `sphinx_docs` module (depends on uv_project)
3. `typecheck` pipeline stage (independent)
4. `docs-api` / `docs-narrative` pipeline split (depends on sphinx_docs)
5. Cross-cutting updates (DEFAULT_GREENFIELD_MODULES, pre-commit template, docs prompt, test updates)
