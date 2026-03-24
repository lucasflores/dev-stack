# Implementation Plan: APM Module Swap

**Branch**: `013-apm-module-swap` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-apm-module-swap/spec.md`

## Summary

Replace dev-stack's internal `mcp_servers` module (~270 LOC of JSON-template rendering) with a new `apm` module that delegates MCP server management to Microsoft's Agent Package Manager (APM) CLI. The `apm` module bootstraps an `apm.yml` manifest seeded with the 5 default servers, invokes `apm install` to deploy agent-native config files, and exposes `dev-stack apm install` / `dev-stack apm audit` CLI subcommands. The legacy `mcp_servers` module is removed from defaults but remains available via opt-in with deprecation warnings.

## Technical Context

**Language/Version**: Python 3.12+ (matches existing dev-stack codebase)
**Primary Dependencies**: Click (CLI framework), PyYAML (apm.yml generation), `subprocess` (APM CLI invocation)
**Storage**: File-based (`apm.yml`, `apm.lock.yaml`, agent-native config dirs)
**Testing**: pytest (existing test framework with `contract/`, `integration/`, `unit/` structure)
**Target Platform**: macOS / Linux (developer workstations)
**Project Type**: Single project (existing `src/dev_stack/` layout)
**Performance Goals**: N/A — CLI tool, not latency-sensitive
**Constraints**: APM CLI must be pre-installed on PATH; no GPU, no network daemons
**Scale/Scope**: ~1 new module (~200 LOC), ~1 new CLI command group, ~5 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Verdict | Evidence |
|---|-----------|---------|----------|
| I | CLI-First Interface | **PASS** | New `dev-stack apm install` and `dev-stack apm audit` subcommands follow existing `dev-stack mcp` pattern. JSON output supported. POSIX exit codes. |
| II | Spec-Driven Development | **PASS** | Full spec.md exists with 16 FRs, 7 SCs, 5 user stories, 3 clarifications encoded. Plan precedes implementation. |
| III | Automation by Default | **PASS** | APM install runs automatically during `dev-stack init`. Lockfile enables reproducible CI-friendly installs. |
| IV | Brownfield Safety | **PASS** | FR-013 requires interactive prompt (skip/merge/overwrite) when `apm.yml` already exists. No silent overwrites. |
| V | AI-Native Architecture | **PASS** | MCP server management is the core concern — APM installs MCP servers for AI agents (Claude, Copilot, Cursor, OpenCode). |
| VI | Local-First Execution | **PASS** | APM runs locally. Registry access is only for initial install, lockfile enables offline reproducibility. |
| VII | Observability & Documentation | **PASS** | Module reports installed/failed servers, audit generates structured reports (SARIF, JSON, markdown). |
| VIII | Modularity & Composability | **PASS** | New `apm` module is independently installable/removable via `ModuleBase`. Legacy `mcp_servers` remains available. No coupling between modules. |

**Gate result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/013-apm-module-swap/
├── plan.md              # This file
├── research.md          # Phase 0: APM CLI research
├── data-model.md        # Phase 1: Entity model
├── quickstart.md        # Phase 1: Quick verification guide
├── contracts/           # Phase 1: API contracts
│   └── cli-contract.md  # CLI subcommand interface spec
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/dev_stack/
├── modules/
│   ├── __init__.py          # MODIFY: add "apm" to DEFAULT_GREENFIELD_MODULES, add auto-import
│   ├── apm.py               # NEW: APMModule(ModuleBase) — core module
│   ├── mcp_servers.py       # MODIFY: add deprecation warning in install()
│   └── base.py              # UNCHANGED: ModuleBase protocol
├── cli/
│   ├── main.py              # MODIFY: import apm_cmd
│   ├── apm_cmd.py           # NEW: Click group for `dev-stack apm install|audit`
│   └── mcp_cmd.py           # UNCHANGED (legacy)
└── templates/
    └── apm/
        └── default-apm.yml  # NEW: default apm.yml template with 5 servers

tests/
├── unit/
│   ├── test_apm_module.py   # NEW: unit tests for APMModule
│   └── test_apm_cmd.py      # NEW: CLI command tests
├── integration/
│   └── test_apm_install.py  # NEW: end-to-end init with APM
└── contract/
    └── test_apm_contract.py # NEW: ModuleBase contract compliance
```

**Structure Decision**: Single project — extends existing `src/dev_stack/modules/` and `src/dev_stack/cli/` layout. No new top-level directories. Follows the exact pattern established by `hooks.py` / `hooks_cmd.py`.

## Complexity Tracking

> One accepted deviation documented below.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV: No explicit rollback for APM-managed agent config files (`.claude/`, `.github/`, etc.) | APM owns these files; dev-stack delegates management entirely. The lockfile enables idempotent re-runs as the recovery mechanism (`apm install` from lockfile restores known-good state). Fail-forward was explicitly chosen in clarification. | Implementing rollback for files managed by an external tool would require shadowing APM's internal file tracking — high complexity, tight coupling, and fragile across APM version changes. |
