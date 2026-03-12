# Implementation Plan: Pipeline Commit Fixes

**Branch**: `011-pipeline-commit-fixes` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-pipeline-commit-fixes/spec.md`

## Summary

Fix four critical defects in the commit pipeline: (1) raw agent stdout (thinking traces, code fences) written as commit messages instead of clean conventional-commit text, (2) pre-commit hook timing prevents git from using the generated message, (3) stale COMMIT_EDITMSG causes false-positive `-m` detection, and (4) `gh copilot --allow-all` lets agents modify staged content mid-pipeline. The fix migrates stages 3–9 to a `prepare-commit-msg` hook, adds response parsing to extract clean messages from agent output, replaces COMMIT_EDITMSG-based detection with hook source arguments, and sandboxes agent invocations during the commit pipeline.

## Technical Context

**Language/Version**: Python 3.11+ (3.12.9 in development)
**Primary Dependencies**: click >=8.1, gitlint-core >=0.19, rich >=13.7, pathspec >=0.12
**Storage**: Filesystem (`.git/COMMIT_EDITMSG`, `.dev-stack/logs/`, `.dev-stack/pending-docs.md`)
**Testing**: pytest with pytest-cov (65% minimum coverage), ruff for linting
**Target Platform**: macOS, Linux (local developer machines)
**Project Type**: Single Python package (`src/dev_stack/`)
**Performance Goals**: Commit pipeline complete within agent timeout (180s max for commit-message stage); fallback within 5s
**Constraints**: Must work within git's hook model; no additional git dependencies beyond standard hooks
**Scale/Scope**: Single-developer local workflow; hooks run on every commit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | PASS | No CLI changes needed; pipeline invoked via existing hook infrastructure |
| II. Spec-Driven Development | PASS | Spec exists at `specs/011-pipeline-commit-fixes/spec.md` with 5 clarifications resolved |
| III. Automation by Default | PASS | Enhances automation — moves from broken to working automated commit messages; adds `prepare-commit-msg` hook |
| IV. Brownfield Safety | PASS | Changes are additive (new hook template, new parser module); existing pre-commit hook behavior preserved for stages 1–2 |
| V. AI-Native Architecture | PASS | Commit messages continue to use coding agents; sandboxing prevents unintended side effects |
| VI. Local-First Execution | PASS | All changes are local git hooks; no cloud dependency |
| VII. Observability & Documentation | PASS | FR-019 adds debug logging for response parsing; advisory doc suggestions written to `.dev-stack/pending-docs.md` |
| VIII. Modularity & Composability | PASS | Response parser is a new independent module; hook redistribution preserves stage independence |

**Constitution gate**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/011-pipeline-commit-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal module interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/dev_stack/
├── pipeline/
│   ├── __init__.py
│   ├── agent_bridge.py      # MODIFY: add sandbox_mode parameter to _build_command
│   ├── commit_format.py     # existing (no changes)
│   ├── response_parser.py   # NEW: extract clean message from raw agent output
│   ├── runner.py            # MODIFY: hook_context awareness for stage routing
│   └── stages.py            # MODIFY: use response_parser, remove _user_message_provided
├── vcs/
│   ├── hooks_runner.py      # MODIFY: add run_prepare_commit_msg_hook()
│   └── ...
└── templates/
    └── hooks/
        ├── pre-commit           # MODIFY: remove stages 3-9, keep lint+typecheck only
        ├── pre-commit.py        # existing (no changes — already lint+typecheck only)
        ├── prepare-commit-msg   # NEW: shell wrapper for prepare-commit-msg hook
        ├── prepare-commit-msg.py # NEW: Python hook running stages 3-9
        ├── commit-msg.py        # existing (no changes)
        └── pre-push.py          # existing (no changes)

tests/
├── unit/
│   ├── test_response_parser.py  # NEW: parser extraction logic
│   ├── test_user_message.py     # MODIFY: update for new detection mechanism
│   └── ...
├── integration/
│   ├── test_commit_message.py   # MODIFY: test end-to-end with prepare-commit-msg
│   ├── test_hooks_lifecycle.py  # MODIFY: add prepare-commit-msg lifecycle tests
│   └── ...
└── contract/
    └── test_cli_hooks.py        # MODIFY: verify hook installation includes prepare-commit-msg
```

**Structure Decision**: Single project layout. All changes are within existing `src/dev_stack/` package. One new module (`response_parser.py`), two new hook templates, modifications to existing modules. No new top-level directories.

## Phase 0: Research

All unknowns resolved. See [research.md](research.md) for findings:
- R1: prepare-commit-msg hook arguments (source values mapped)
- R2: Git hook execution order confirmed
- R3: Editor interaction — hook writes before editor opens
- R4: Copilot sandbox via `--deny-tool='write'` + selective `--allow-tool`
- R5: Last-code-fence parsing heuristic with fallback
- R6: Pre-commit hook → stages 1–2 only (template fix)

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) — defines 6 entities:
- `ParsedCommitMessage` — immutable value object for extracted messages
- `ExtractionMethod` — enum: `CODE_FENCE`, `PLAIN_TEXT`
- `HookContext` — hook name, message file, source arg, commit SHA
- `StagedSnapshot` — diff hash pair for integrity verification
- `AgentInvocationMode` — enum: `SANDBOXED`, `FULL_ACCESS`
- `AdvisoryDocSuggestion` — captured doc changes for `.dev-stack/pending-docs.md`

### Contracts

| Contract | File | Scope |
|----------|------|-------|
| Response Parser | [contracts/response-parser.md](contracts/response-parser.md) | New `response_parser.py` module API |
| Hook Context & Stage Routing | [contracts/hook-context.md](contracts/hook-context.md) | `prepare-commit-msg` hook, stage filtering, hook templates |
| Agent Sandbox | [contracts/agent-sandbox.md](contracts/agent-sandbox.md) | `sandbox` param, `--deny-tool` flags, staged snapshot protection |
| Advisory Docs | [contracts/advisory-docs.md](contracts/advisory-docs.md) | `_execute_docs_narrative_stage()` advisory mode |
| Debug Logging | [contracts/debug-logging.md](contracts/debug-logging.md) | `DEV_STACK_DEBUG=1` file-based logging |

### Quickstart

See [quickstart.md](quickstart.md) — developer guide covering new files, modified files, stage distribution, testing examples, and debug workflow.

## Constitution Re-check (Post-Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Interface | PASS | No CLI surface changes |
| II. Spec-Driven Development | PASS | All contracts trace to FRs in spec |
| III. Automation by Default | PASS | prepare-commit-msg hook automates message generation correctly |
| IV. Brownfield Safety | PASS | Additive — new module, new hook templates; existing behavior preserved for non-hook CLI |
| V. AI-Native Architecture | PASS | Sandbox mode preserves AI-driven generation while preventing side effects |
| VI. Local-First Execution | PASS | All local — no network or cloud dependency |
| VII. Observability & Documentation | PASS | Debug logging via `DEV_STACK_DEBUG=1`; advisory docs to `pending-docs.md` |
| VIII. Modularity & Composability | PASS | `response_parser` is independent; sandbox logic isolated in `agent_bridge` |

**Post-design gate**: PASS — no new violations.

**Note on Principle VII (Observability & Documentation)**: The constitution states "README and API documentation MUST be auto-updated as part of the pre-commit pipeline." During hook-context execution, doc agent stages still run and produce suggestions, but those suggestions are saved to `.dev-stack/pending-docs.md` (advisory mode) rather than applied directly — to protect staged content integrity (Principle IV). This is a compatible narrowing: the automation runs, suggestions are produced, application is deferred to the developer. Principle IV (brownfield safety) takes precedence over immediate auto-application during the commit flow.

## Complexity Tracking

No constitution violations detected. Table intentionally empty.
