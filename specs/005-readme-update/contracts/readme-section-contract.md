# Contract: README Section Structure

**Feature**: 005-readme-update  
**Date**: 2026-03-09

## Purpose

This contract defines the exact section order, heading levels, and content types for the updated `README.md`. It serves as the authoritative reference during implementation.

## Section Contract

### Section 1: Title + Tagline

```markdown
# Dev-Stack Ecosystem

> One-command bootstrap — 9 pluggable modules, 8-stage pipeline, CodeBoarding visualization, and VCS best-practices enforcement for any Python repo.
```

**Rules**: Single `<h1>`, single blockquote. No Table of Contents inline — TOC follows immediately.

---

### Section 2: Table of Contents

```markdown
- [What Is Dev-Stack?](#what-is-dev-stack)
- [Key Capabilities](#key-capabilities)
- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Install Dev-Stack In Your Repo](#install-dev-stack-in-your-repo)
- [CLI Essentials](#cli-essentials)
- [Module Catalog](#module-catalog)
- [Automation Pipeline](#automation-pipeline)
- [Visualization Workflow](#visualization-workflow)
- [Validation Checklist](#validation-checklist)
- [Configuration](#configuration)
- [Repository Layout](#repository-layout)
- [Architecture Snapshot](#architecture-snapshot)
- [Development](#development)
- [Spec Assets](#spec-assets)
```

**Rules**: Exactly 15 entries. Each links to an `<h2>`.

---

### Section 3: What Is Dev-Stack?

**Heading**: `## What Is Dev-Stack?`  
**Content**: Prose paragraph + bullet list  
**FR Coverage**: FR-001 (9 modules mentioned), FR-002 (8-stage pipeline)  
**Must mention**: CodeBoarding (not D2), 8-stage pipeline, VCS practices, UV Project scaffolding  
**Must NOT mention**: D2, six-stage, noodles

---

### Section 4: Key Capabilities

**Heading**: `## Key Capabilities`  
**Content**: Emoji bullet list (5–7 items)  
**FR Coverage**: FR-003, FR-007, FR-015, FR-016  
**New items**: VCS enforcement, Python project scaffolding, constitutional agent instructions

---

### Section 5: Prerequisites

**Heading**: `## Prerequisites`  
**Content**: Single table with columns: Tool | Purpose | Required?  
**FR Coverage**: FR-009  
**Row count**: 10 rows (4 required, 6 optional)  
**Must NOT contain**: `d2` in any form

---

### Section 6: Quickstart

**Heading**: `## Quickstart`  
**Content**: Code blocks for clone + editable install + smoke test  
**Must NOT contain**: `d2` in brew install

---

### Section 7: Install Dev-Stack In Your Repo

**Heading**: `## Install Dev-Stack In Your Repo`  
**Content**: 3 numbered subsections (Install CLI, Bootstrap, Review assets)  
**FR Coverage**: FR-010, FR-015  
**Assets table**: Must match data-model Generated Assets entity (15 rows)

---

### Section 8: CLI Essentials

**Heading**: `## CLI Essentials`  
**Content**: Single command table  
**FR Coverage**: FR-003, FR-006, FR-007  
**Row count**: 12 commands — init, update, rollback, `mcp install|verify`, `pipeline run`, visualize, status, changelog, `hooks status`, pr, release, version (each row = one table entry; subcommands shown inline)
**Must include**: `--depth-level`, `--incremental`, `--no-readme`, `--timeout` for visualize
**Footer note**: `--json` and `--dry-run` support

---

### Section 9: Module Catalog

**Heading**: `## Module Catalog`  
**Content**: Table with columns: Module | Managed Assets | Highlights  
**FR Coverage**: FR-001, FR-007, FR-014, FR-016  
**Row count**: 9 modules  
**VCS distribution**: VCS Hooks module row describes commit linting, branch naming, signing, constitutional instructions

---

### Section 10: Automation Pipeline

**Heading**: `## Automation Pipeline`  
**Content**: Table with columns: Stage | Mode | Description  
**FR Coverage**: FR-002  
**Row count**: 8 stages  
**Must match**: `build_pipeline_stages()` order exactly  
**Footer notes**: Stages 1–5 hard gate (halt on fail), stages 6–8 soft gate (warn, allow with `--force`)

---

### Section 11: Visualization Workflow

**Heading**: `## Visualization Workflow`  
**Content**: 3 numbered steps  
**FR Coverage**: FR-004, FR-005, FR-006  
**Must describe**: CodeBoarding CLI invocation, Mermaid output, README managed marker injection  
**Must mention**: `--depth-level` default (2), per-folder sub-diagrams, `--no-readme` flag  
**Must NOT contain**: D2, d2_gen, schema_gen, noodles, infra-console, SVG/PNG rendering

---

### Section 12: Validation Checklist

**Heading**: `## Validation Checklist`  
**Content**: 6–8 numbered items with code examples  
**Must reference**: [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md)

---

### Section 13: Configuration

**Heading**: `## Configuration`  
**Content**: Code block showing `[tool.dev-stack.*]` sections + explanation  
**FR Coverage**: FR-008  
**Subsections**: Branch naming pattern, hook selection, signing settings

---

### Section 14: Repository Layout

**Heading**: `## Repository Layout`  
**Content**: ASCII tree  
**FR Coverage**: FR-011, FR-013  
**Must include**: `vcs/`, `rules/`, `visualization/`, `brownfield/`, `pipeline/`, `modules/`, `cli/`, `templates/`  
**Must include**: `specs/001–004/` (all four spec directories)

---

### Section 15: Architecture Snapshot

**Heading**: `## Architecture Snapshot`  
**Content**: Bullet list describing each package  
**FR Coverage**: FR-012  
**Must include**: `vcs/` (commit parsing, branch validation, PR/changelog/release, signing, scope), `rules/` (gitlint custom rules for conventional commits and trailers), `visualization/` (CodeBoarding runner, output parser, README injector, incremental diffing)

---

### Section 16: Development

**Heading**: `## Development`  
**Content**: Code blocks for lint/test/visualize  
**Must NOT contain**: `d2` references

---

### Section 17: Spec Assets

**Heading**: `## Spec Assets`  
**Content**: Indented link lists grouped by spec directory  
**FR Coverage**: FR-013  
**Must reference**: All 4 spec directories (001, 002, 003, 004) with links to each spec.md

---

## Validation Rules

1. **No duplicate topics**: Each topic appears in exactly one section
2. **No D2 references**: Zero occurrences of `d2`, `D2`, `d2_gen`, `schema_gen`, `noodles`, `infra-console`
3. **Count accuracy**: 9 modules, 12 CLI table rows (each subcommand counted as its parent entry), 8 pipeline stages, 10 prerequisites
4. **Link validity**: All relative links resolve to existing files
5. **Code block correctness**: All bash examples use correct command syntax
