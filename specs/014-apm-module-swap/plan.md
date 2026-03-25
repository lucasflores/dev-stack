# Implementation Plan: Remove SpecKit Module — Consolidate Under APM

**Branch**: `014-apm-module-swap` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-apm-module-swap/spec.md`

## Summary

Remove the `speckit` module (~370 LOC) from dev-stack and consolidate all agent-package management under the existing `apm` module. The `apm.yml` template is expanded to declare Agency reviewers, LazySpecKit prompts/reviewers, and MCP servers — everything speckit previously installed except the `.specify/` template tree, which is now handled by `specify init` (documented in README). The module registry defaults are updated, the speckit source/templates/tests are deleted (~3,600 lines net removal), and a migration handler ensures existing projects with `[modules.speckit]` in `dev-stack.toml` upgrade gracefully with a deprecation marker.

## Technical Context

**Language/Version**: Python 3.11+ (pyproject.toml: `requires-python = ">=3.11"`)
**Primary Dependencies**: Click (CLI), PyYAML (apm.yml generation), `subprocess` (APM CLI invocation), `tomli-w` (TOML writing), `packaging` (version comparison)
**Storage**: File-based (`apm.yml`, `apm.lock.yaml`, `dev-stack.toml`)
**Testing**: pytest with `contract/`, `integration/`, `unit/` structure; coverage threshold 65%
**Target Platform**: macOS / Linux (developer workstations)
**Project Type**: Single project (existing `src/dev_stack/` layout)
**Performance Goals**: N/A — CLI tool, not latency-sensitive
**Constraints**: APM CLI >= 0.8.0 must be pre-installed on PATH; no GPU, no network daemons
**Scale/Scope**: Net deletion of ~2,700 lines; small additions to migration handler and apm.yml template

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Verdict | Evidence |
|---|-----------|---------|----------|
| I | CLI-First Interface | **PASS** | No new CLI commands needed. Existing `dev-stack init`, `dev-stack update`, and `dev-stack apm install` cover all workflows. Removal doesn't reduce CLI capabilities. |
| II | Spec-Driven Development | **PASS** | Full spec.md with 5 user stories, 10 FRs, 6 SCs, 3 clarifications encoded. Plan precedes implementation. |
| III | Automation by Default | **PASS** | APM install runs automatically during `dev-stack init`. The only new manual step (`specify init`) is documented in README and is a one-time post-init action. |
| IV | Brownfield Safety | **PASS** | FR-004 marks `[modules.speckit]` as `deprecated = true` in existing `dev-stack.toml` — no deletion of user config. Clarification Q3 confirms no cleanup of leftover artifacts. |
| V | AI-Native Architecture | **PASS** | APM manages all MCP servers and agent dependencies. Agency reviewers and LazySpecKit prompts are pulled via APM's native dependency resolution. |
| VI | Local-First Execution | **PASS** | All operations are local. APM resolves from git sources locally. No new cloud dependencies. |
| VII | Observability & Documentation | **PASS** | FR-006 requires README update with post-init instructions. Migration handler emits informational message for deprecated speckit. |
| VIII | Modularity & Composability | **PASS** | Removing speckit is an exercise in correct modularity — no other module depends on it. APM absorbs its responsibilities cleanly. |

**Gate result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/014-apm-module-swap/
├── plan.md              # This file
├── research.md          # Phase 0: Dependency pinning, migration patterns, apm.yml format
├── data-model.md        # Phase 1: Entity model for migration handler and expanded apm.yml
├── quickstart.md        # Phase 1: Verification steps
├── contracts/           # Phase 1: Migration handler contract
│   └── migration-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/dev_stack/
├── modules/
│   ├── __init__.py          # MODIFY: remove "speckit" from DEFAULT_GREENFIELD_MODULES, remove speckit import
│   ├── apm.py               # MODIFY: update _merge_manifest() to handle dependencies.apm section
│   ├── speckit.py           # DELETE: entire module (~370 LOC)
│   └── base.py              # UNCHANGED
├── cli/
│   └── update_cmd.py        # MODIFY: add migration handling for deprecated speckit entries
├── manifest.py              # MODIFY: remove "speckit" from DEFAULT_MODULES
└── templates/
    ├── apm/
    │   └── default-apm.yml  # MODIFY: expand with Agency reviewers + LazySpecKit deps
    ├── speckit/              # DELETE: entire directory (vendored speckit templates)
    └── lazyspeckit/          # DELETE: entire directory (vendored LazySpecKit files)

tests/
├── unit/
│   ├── test_speckit_lazyspeckit.py   # DELETE
│   ├── test_speckit_module.py        # DELETE (if exists)
│   ├── test_modules_registry.py      # MODIFY: update DEFAULT_GREENFIELD_MODULES assertion
│   └── test_apm_module.py            # MODIFY: add tests for expanded template
├── integration/
│   └── test_speckit.py               # DELETE (if exists)
└── contract/
    └── test_module_interface.py       # VERIFY: speckit no longer in registry
```

**Structure Decision**: Single project — extends existing `src/dev_stack/` layout. This is primarily a deletion feature with targeted modifications to `modules/__init__.py`, `manifest.py`, `update_cmd.py`, and the `apm.yml` template. No new top-level directories.

## Complexity Tracking

> No constitution violations. All principles pass cleanly.
