# Research: README Comprehensive Update

**Feature**: 005-readme-update  
**Date**: 2026-03-09

## 1. Current README Audit — Duplicate Sections

The current README (~322 lines) contains the following duplicate content:

| Topic | First Occurrence | Second Occurrence | Decision |
|-------|-----------------|-------------------|----------|
| Prerequisites | "Quickstart" table (L48–54) | "Requirements" table (L229–235) | Consolidate into single table in Quickstart with Required? column |
| CLI Commands | "CLI Essentials" table (L124–132) | "Core CLI Commands" table (L257–265) | Consolidate into single "CLI Essentials" table |
| Validation | "Validation Checklist" section (L160–177) | "Validation Workflow" section (L269–284) | Consolidate into single "Validation Checklist" section |
| Installation | "Quickstart" code block (L56–65) | "Getting Started" code block (L237–247) | Consolidate into single "Quickstart" section |
| Repository tree | "Repository Map" tree (L183–197) | "Repository Layout" tree (L296–309) | Consolidate into single "Repository Layout" section |
| Spec links | "Spec Assets" list (L207–214) | "Additional Resources" list (L314–319) | Consolidate into single "Spec Assets" section |
| Development workflow | "Development Workflow" code block (L200–205) | "Development" code block (L289–296) | Consolidate into single "Development" section |

**Total duplicate sections**: 7 — all will be merged per Clarification Q1.

## 2. Stale Content — Removed Features

| Stale Content | Lines | Replacement |
|---------------|-------|-------------|
| "six-stage automation pipeline" | L22, L105, L259 | "eight-stage automation pipeline" |
| "D2 generator" / "D2" | L26, L54, L128, L156, L232, L297 | "CodeBoarding CLI + Mermaid.js" |
| `d2 (optional)` prerequisite | L53, L232 | Remove entirely |
| `brew install ... d2` | L57, L239 | Remove `d2` from command |
| `d2_gen.py`, `schema_gen.py` | L148–153 | Replace with CodeBoarding workflow |
| `docs/diagrams/overview.svg (plus per-node SVGs)` | L116 | Replace with `.codeboarding/` + README Mermaid injection |
| "noodles-inspired" | L128, L264 | Remove — CodeBoarding is its own pattern |
| "Infra-console D2 template" | L141 | Replace with CodeBoarding description |
| `AgentUnavailableError` visualization fallback | L155 | Update to CodeBoarding error handling |

## 3. Missing Content — New Features

### 3a. New Modules (from source: `src/dev_stack/modules/`)

| Module File | README Module Name | Status in README |
|-------------|--------------------|------------------|
| `hooks.py` | Hooks | ✅ Present |
| `speckit.py` | Spec Kit | ✅ Present |
| `mcp_servers.py` | MCP Servers | ✅ Present |
| `ci_workflows.py` | CI Workflows | ✅ Present |
| `docker.py` | Docker | ✅ Present |
| `visualization.py` | Visualization | ✅ Present (but description stale — D2) |
| `uv_project.py` | UV Project | ❌ Missing |
| `sphinx_docs.py` | Sphinx Docs | ❌ Missing |
| `vcs_hooks.py` | VCS Hooks | ❌ Missing |

### 3b. New CLI Commands (from source: `src/dev_stack/cli/`)

| CLI File | Command | Status in README |
|----------|---------|------------------|
| `init_cmd.py` | `init` | ✅ Present |
| `update_cmd.py` | `update` | ✅ Present |
| `rollback_cmd.py` | `rollback` | ✅ Present |
| `mcp_cmd.py` | `mcp install\|verify` | ✅ Present |
| `pipeline_cmd.py` | `pipeline run` | ✅ Present |
| `visualize_cmd.py` | `visualize` | ✅ Present (flags stale) |
| `status_cmd.py` | `status` | ✅ Present |
| `changelog_cmd.py` | `changelog` | ❌ Missing |
| `hooks_cmd.py` | `hooks status` | ❌ Missing |
| `pr_cmd.py` | `pr` | ❌ Missing |
| `release_cmd.py` | `release` | ❌ Missing |

### 3c. Pipeline Stages (from source: `stages.py::build_pipeline_stages()`)

| Order | Name | Gate | Status in README |
|-------|------|------|------------------|
| 1 | lint | Hard | ✅ Present |
| 2 | typecheck | Hard | ❌ Missing |
| 3 | test | Hard | ✅ Present (renumbered from 2→3) |
| 4 | security | Hard | ✅ Present (renumbered from 3→4) |
| 5 | docs-api | Hard | ❌ Missing (was single "docs" soft gate) |
| 6 | docs-narrative | Soft | ❌ Missing (was single "docs" soft gate) |
| 7 | infra-sync | Soft | ✅ Present (renumbered from 5→7) |
| 8 | commit-message | Soft | ✅ Present (renumbered from 6→8) |

### 3d. New Templates

| Template | Status in README |
|----------|------------------|
| `cliff.toml` | ❌ Missing |
| `constitution-template.md` | ❌ Missing |
| `instructions.md` | ❌ Missing |
| `pr-template.md` | ❌ Missing |

### 3e. New Source Packages

| Package | Status in README |
|---------|------------------|
| `src/dev_stack/vcs/` | ❌ Missing from architecture snapshot & repo layout |
| `src/dev_stack/rules/` | ❌ Missing from architecture snapshot & repo layout |

### 3f. Spec Directories

| Directory | Status in README |
|-----------|------------------|
| `specs/001-dev-stack-ecosystem/` | ✅ Referenced |
| `specs/002-init-pipeline-enhancements/` | ❌ Missing |
| `specs/003-codeboarding-viz/` | ❌ Missing |
| `specs/004-vcs-best-practices/` | ❌ Missing |

### 3g. New Generated Assets

| Asset | Status in README |
|-------|------------------|
| `.git/hooks/commit-msg` | ❌ Missing from generated assets table |
| `.git/hooks/pre-push` | ❌ Missing from generated assets table |
| `docs/conf.py`, `docs/index.rst`, `docs/Makefile` | ❌ Missing |
| `constitution-template.md` | ❌ Missing |
| `.dev-stack/instructions.md` | ❌ Missing |
| `cliff.toml` | ❌ Missing |
| `.codeboarding/` output directory | ❌ Missing |

## 4. Visualization Workflow Replacement

**Old workflow** (D2-based, 4 steps):
1. Scan → `scanner.py` concatenates files
2. Schema → `schema_gen.py` shells out to agent
3. Generate D2 → `d2_gen.py` converts to D2 markup
4. Render → `visualize_cmd.py` runs `d2` CLI

**New workflow** (CodeBoarding-based, 3 steps):
1. Invoke → `codeboarding_runner.py` runs `codeboarding` CLI as subprocess (300s timeout)
2. Parse → `output_parser.py` reads `.codeboarding/analysis.json` for Mermaid diagrams
3. Inject → `readme_injector.py` writes Mermaid blocks into README files with managed markers

**New CLI flags**: `--depth-level` (default 2), `--incremental`, `--no-readme`, `--timeout`

## 5. Section Consolidation Plan

**Target section order** (per clarification: overview → install → usage → reference):

1. What Is Dev-Stack?
2. Key Capabilities
3. Prerequisites (single table with Required? column)
4. Quickstart (contributor install — clone + editable)
5. Install Dev-Stack In Your Repo (consumer install — wheel/PyPI)
6. CLI Essentials (single consolidated table)
7. Module Catalog (9 modules, VCS Hooks distributed here)
8. Automation Pipeline (8 stages)
9. Visualization Workflow (CodeBoarding)
10. Validation Checklist (single consolidated section)
11. Configuration (pyproject.toml `[tool.dev-stack.*]` sections)
12. Repository Layout (single consolidated tree)
13. Architecture Snapshot
14. Development (single consolidated section)
15. Spec Assets (all 4 spec directories)

**Removed sections**: Requirements (duplicate of Prerequisites), Getting Started (duplicate of Quickstart), Core CLI Commands (duplicate of CLI Essentials), Validation Workflow (duplicate of Validation Checklist), Repository Map (duplicate of Repository Layout), Additional Resources (duplicate of Spec Assets), Development Workflow (duplicate of Development).

## 6. Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Consolidate 7 duplicate sections | Clarification Q1 — single authoritative sections reduce contradictions | Keep both (rejected: maintenance burden, unjustified repetition) |
| Distribute VCS into existing sections | Clarification Q2 — no standalone VCS section; information where users expect it | Dedicated VCS section (rejected: breaks scanning flow) |
| Single prerequisites with Required? column | Clarification Q3 — single scannable table, clear optional marking | Separate required/optional tables (rejected: two tables to maintain) |
| Remove all D2 references | Spec FR-004 — D2 is fully replaced by CodeBoarding | Keep D2 as optional (rejected: no longer in codebase) |
