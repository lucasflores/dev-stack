# Implementation Plan: CodeBoarding Visualization

**Branch**: `003-codeboarding-viz` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-codeboarding-viz/spec.md`

## Summary

Replace dev-stack's D2-based visualization module with a CodeBoarding CLI wrapper that generates Mermaid.js architecture diagrams. The implementation invokes CodeBoarding as a subprocess, parses its `analysis.json` output to discover components, extracts pre-rendered Mermaid diagrams from markdown files, and injects them into repository README files using brownfield managed-section markers. A new per-folder sub-diagram capability is added, tracked by an injection ledger for clean uninstall.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click >=8.1, rich, pathspec (existing); CodeBoarding CLI (external subprocess, not imported)
**Storage**: File-based JSON (.codeboarding/analysis.json, .codeboarding/injected-readmes.json, .dev-stack/viz/manifest.json)
**Testing**: pytest (unit + integration + contract tests)
**Target Platform**: macOS, Linux (CLI tool)
**Project Type**: single
**Performance Goals**: Full analysis depends on CodeBoarding (minutes); dev-stack overhead < 5s for parsing + injection
**Constraints**: 300s default subprocess timeout (configurable via --timeout); no Python library import of CodeBoarding
**Scale/Scope**: Handles repos with up to hundreds of components; injection into dozens of README files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | CLI-First Interface | **PASS** | `dev-stack visualize` with --incremental, --depth-level, --no-readme, --timeout, --json flags. POSIX exit codes. |
| II | Spec-Driven Development | **PASS** | Full spec with 6 user stories, 20 FRs, 8 success criteria before implementation. |
| III | Automation by Default | **PASS** | CodeBoarding invocation, output parsing, README injection all automated. Idempotent runs. |
| IV | Brownfield Safety | **PASS** | Managed section markers preserve user README content. Injection ledger enables targeted cleanup. |
| V | AI-Native Architecture | **PASS** | CodeBoarding uses LLM-driven analysis. subprocess-only boundary maintained. |
| VI | Local-First Execution | **PASS** | All analysis and injection runs locally. No remote services required by dev-stack itself. |
| VII | Observability and Documentation | **PASS** | --json structured output, --verbose logging, dev-stack status health reporting. |
| VIII | Modularity and Composability | **PASS** | VisualizationModule implements ModuleBase contract. New files (runner, parser, injector) are composable units. |

**Gate result**: ALL PASS — no violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/003-codeboarding-viz/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: CodeBoarding CLI research
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Usage guide
├── contracts/
│   ├── module-contract.md  # VisualizationModule lifecycle
│   └── cli-contract.md     # dev-stack visualize command
├── checklists/
│   └── requirements.md     # Quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/dev_stack/
├── modules/
│   └── visualization.py         # REWRITE: D2 -> CodeBoarding module lifecycle
├── cli/
│   └── visualize_cmd.py         # REWRITE: D2 -> CodeBoarding CLI command
├── visualization/
│   ├── codeboarding_runner.py   # NEW: subprocess invocation of CodeBoarding CLI
│   ├── output_parser.py         # NEW: parse analysis.json + extract Mermaid from .md files
│   ├── readme_injector.py       # NEW: managed section injection + ledger management
│   ├── incremental.py           # RETAIN: ManifestStore for hash-based change detection
│   ├── scanner.py               # RETAIN: SourceScanner for file snapshot building
│   ├── d2_gen.py                # DELETE: D2 diagram generator
│   ├── schema_gen.py            # DELETE: LLM-based schema generator
│   └── templates/               # DELETE: D2 template files
├── brownfield/
│   └── markers.py               # UNCHANGED: managed section read/write
└── errors.py                    # EXTEND: add CodeBoardingError if needed

tests/
├── unit/
│   ├── test_codeboarding_runner.py  # NEW: subprocess mock tests
│   ├── test_output_parser.py        # NEW: analysis.json parsing tests
│   ├── test_readme_injector.py      # NEW: injection + ledger tests
│   └── test_d2_gen.py               # DELETE
├── integration/
│   └── test_visualize.py            # NEW: end-to-end visualize command tests
└── contract/
    └── test_module_interface.py     # UPDATE: add visualization module assertions
```

**Structure Decision**: Single project layout retained. Three new files under visualization/ (runner, parser, injector) decompose the CodeBoarding integration into focused, testable units. D2-related files are deleted.

## Phase 0 Artifacts

- [research.md](research.md) — 9 research items covering CLI entry point, output format, analysis.json schema, Mermaid extraction, depth defaults, component-to-folder mapping, incremental integration, error handling, and ledger format.

### Key Research Findings

| Finding | Impact |
|---------|--------|
| CodeBoarding CLI entry point is `codeboarding` (PyPI package) | Confirms FR-001 invocation |
| No output.json — index is `analysis.json` | FR-002 correction needed |
| Default --depth-level is 1 (top-level only) | dev-stack defaults to 2 for sub-diagrams |
| Component .md files: name with underscores + .md | Filename derivation for parser |
| Mermaid is first fenced code block in each .md | Extraction strategy confirmed |

## Phase 1 Artifacts

- [data-model.md](data-model.md) — 9 entities: AnalysisIndex, Component, ComponentRelation, KeyEntity, ComponentMarkdown, InjectionLedger, LedgerEntry, VisualizationManifest, FileEntry
- [contracts/module-contract.md](contracts/module-contract.md) — VisualizationModule lifecycle (install/uninstall/update/verify)
- [contracts/cli-contract.md](contracts/cli-contract.md) — dev-stack visualize command with flags, JSON output schema, error handling
- [quickstart.md](quickstart.md) — Usage guide with prerequisites, common flags, troubleshooting

### Post-Design Constitution Re-Check

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | CLI-First Interface | **PASS** | CLI contract fully defined with 6 flags, structured JSON, POSIX exits |
| II | Spec-Driven Development | **PASS** | All artifacts generated from spec before implementation |
| III | Automation by Default | **PASS** | Fully automated: subprocess, parse, inject, ledger. Idempotent. |
| IV | Brownfield Safety | **PASS** | Managed markers via markers.py. Ledger-based cleanup. Legacy D2 migration. |
| V | AI-Native Architecture | **PASS** | subprocess boundary to CodeBoarding; no library coupling |
| VI | Local-First Execution | **PASS** | Zero remote calls from dev-stack. CodeBoarding LLM calls are its concern. |
| VII | Observability and Documentation | **PASS** | JSON output, verbose mode, status health check, per-component warnings |
| VIII | Modularity and Composability | **PASS** | 3 new focused modules (runner/parser/injector) + existing ManifestStore |

**Post-design gate result**: ALL PASS — design is constitution-compliant.
