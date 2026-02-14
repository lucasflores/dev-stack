# Implementation Plan: Dev-Stack Ecosystem

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-dev-stack-ecosystem/spec.md`

## Summary

Build a CLI tool (`dev-stack`) that initializes or augments repositories with a full automation
and AI capabilities suite. The system is modular (hooks, MCP servers, CI, Docker, visualization,
Spec Kit), uses coding agent CLIs as the AI backbone (not direct LLM API calls), and stores its
configuration in `dev-stack.toml` at the repo root. The visualization module adapts the noodles
project's pipeline (scan -> combine -> agent-analyze -> D2 diagram) replacing direct OpenAI/Gemini
API calls with coding agent CLI invocations. The commit message agent generates structured messages
that serve as persistent memory for coding agents.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `click` (CLI framework), `tomllib` (stdlib TOML reader) / `tomli-w` (TOML writer), `rich` (terminal output), `d2` CLI (diagrams)
**Storage**: File-based -- `dev-stack.toml` manifest, `.dev-stack/` working directory, `.specify/` for Spec Kit
**Testing**: `pytest` with `pytest-cov`, contract tests for CLI output schemas
**Target Platform**: macOS, Linux (POSIX)
**Project Type**: Single CLI project
**Performance Goals**: Pipeline <60s for <50 files, <2min for <200, <5min for <500; init <30s excluding downloads
**Constraints**: Offline-capable for hooks/local configs; no secrets in files; coding agent CLI required for generative stages
**Scale/Scope**: Target repositories with 1-500 source files; 6 independent modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. CLI-First Interface | PASS | `dev-stack init`, `update`, `rollback`, `mcp install`, `visualize` commands planned |
| II. Spec-Driven Development | PASS | This plan is itself a spec artifact; Spec Kit is a core module |
| III. Automation by Default | PASS | 6-stage pre-commit pipeline automates lint/test/security/docs/infra/commit |
| IV. Brownfield Safety | PASS | Conflict detection, per-file diffs, marker-delimited sections, git-based rollback |
| V. AI-Native Architecture | PASS | Coding agent CLI invocation (not API calls), structured commit memory, MCP servers |
| VI. Local-First Execution | PASS | All hooks run locally; CI justified per-job; Docker for reproducibility |
| VII. Observability & Documentation | PASS | D2 visualization, auto-docs agent, structured logging |
| VIII. Modularity & Composability | PASS | 6 independent modules with explicit dependency manifest |

**Gate result: PASS -- no violations. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/001-dev-stack-ecosystem/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity model
├── quickstart.md        # Phase 1: developer quick-start
├── contracts/           # Phase 1: CLI & module interfaces
│   ├── cli-contract.md
│   ├── module-contract.md
│   └── agent-invocation-contract.md
└── tasks.md             # Phase 2: tasks (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── dev_stack/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # click CLI entry point
│   │   ├── init_cmd.py          # dev-stack init
│   │   ├── update_cmd.py        # dev-stack update
│   │   ├── rollback_cmd.py      # dev-stack rollback
│   │   ├── mcp_cmd.py           # dev-stack mcp install/verify
│   │   └── visualize_cmd.py     # dev-stack visualize
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py              # Module ABC
│   │   ├── hooks.py             # Pre-commit pipeline module
│   │   ├── mcp_servers.py       # MCP server configuration module
│   │   ├── ci_workflows.py      # CI workflow generation module
│   │   ├── docker.py            # Dockerfile generation module
│   │   ├── visualization.py     # D2 diagram generation module
│   │   └── speckit.py           # Spec Kit integration module
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── runner.py            # Pipeline orchestrator
│   │   ├── stages.py            # Stage definitions (lint, test, security, etc.)
│   │   └── agent_bridge.py      # Coding agent CLI invocation abstraction
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── scanner.py           # Source file scanning (noodles-inspired)
│   │   ├── schema_gen.py        # Agent-driven schema generation
│   │   ├── d2_gen.py            # JSON schema -> D2 diagram (deterministic)
│   │   ├── incremental.py       # Manifest diff & incremental updates
│   │   └── templates/
│   │       └── overview.d2      # D2 template
│   ├── brownfield/
│   │   ├── __init__.py
│   │   ├── conflict.py          # Conflict detection & diff presentation
│   │   ├── markers.py           # Marker-delimited section management
│   │   └── rollback.py          # Git-based rollback mechanism
│   ├── manifest.py              # dev-stack.toml reader/writer
│   └── config.py                # Global config, agent detection, env var validation
├── templates/                     # Scaffolding templates for generated files
│   ├── hooks/
│   ├── ci/
│   ├── docker/
│   └── mcp/
tests/
├── unit/
│   ├── test_manifest.py
│   ├── test_conflict.py
│   ├── test_markers.py
│   ├── test_d2_gen.py
│   └── test_pipeline.py
├── integration/
│   ├── test_init_greenfield.py
│   ├── test_init_brownfield.py
│   ├── test_update.py
│   └── test_rollback.py
└── contract/
    ├── test_cli_json_output.py
    └── test_module_interface.py
```

**Structure Decision**: Single CLI project. All source under `src/dev_stack/` for a
standard Python package layout. `templates/` at project root holds scaffold files that
get copied during `init`. Tests split into unit, integration, and contract tiers.

## Complexity Tracking

> No Constitution Check violations -- this section is empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| -- | -- | -- |
