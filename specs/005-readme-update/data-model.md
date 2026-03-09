# Data Model: README Comprehensive Update

**Feature**: 005-readme-update  
**Date**: 2026-03-09

## Entity: README Section

The README is modeled as 15 ordered content sections. Each section is an atomic unit of content that maps to one or more spec functional requirements.

> **Note**: Section numbers below are 1-indexed content sections. In contracts/readme-section-contract.md, §1=Title and §2=TOC precede these, so contract §N = data-model section #(N−2).

| Section # | Section Name | FR Coverage | Content Type | Consolidates |
|-----------|-------------|-------------|--------------|--------------|
| 1 | What Is Dev-Stack? | FR-001, FR-002 | Prose + bullet list | — |
| 2 | Key Capabilities | FR-003, FR-007, FR-015, FR-016 | Emoji bullet list | — |
| 3 | Prerequisites | FR-009 | Table (Tool, Purpose, Required?) | Quickstart prereqs + Requirements table |
| 4 | Quickstart | — | Code blocks | Quickstart + Getting Started |
| 5 | Install Dev-Stack In Your Repo | FR-010, FR-015 | Numbered steps + table | — |
| 6 | CLI Essentials | FR-003, FR-007 | Command table | CLI Essentials + Core CLI Commands |
| 7 | Module Catalog | FR-001, FR-007, FR-014, FR-016 | Module table | — |
| 8 | Automation Pipeline | FR-002 | Stage table | — |
| 9 | Visualization Workflow | FR-004, FR-005, FR-006 | Numbered steps | — |
| 10 | Validation Checklist | — | Numbered checklist | Validation Checklist + Validation Workflow |
| 11 | Configuration | FR-008 | Code + table | New section |
| 12 | Repository Layout | FR-011 | ASCII tree | Repository Map + Repository Layout |
| 13 | Architecture Snapshot | FR-012 | Bullet list | — |
| 14 | Development | — | Code blocks | Development Workflow + Development |
| 15 | Spec Assets | FR-013 | Link list | Spec Assets + Additional Resources |

## Entity: Module Catalog Entry

Each module row in the Module Catalog table has these fields:

| Field | Description | Source of Truth |
|-------|-------------|-----------------|
| Module | Human-readable name | Module class docstring or `__init__.py` |
| Managed Assets | Files/dirs the module creates or manages | Module's `preview_files()` method |
| Highlights | Key behavior and dependencies | Spec + source |

### Complete Module List (9 modules)

| Module | Managed Assets | Highlights |
|--------|----------------|------------|
| Hooks | `.pre-commit-config.yaml`, `scripts/hooks/*` | 8-stage automation pipeline wired into git hooks |
| Spec Kit | `.specify/` scaffold | Ships constitution, memory, templates, and scripts |
| MCP Servers | `.claude/` or `.github/` configs | Auto-installs Context7, GitHub, Sequential Thinking, Hugging Face, NotebookLM servers |
| CI Workflows | `.github/workflows/dev-stack-*.yml` | Opinionated multi-job CI with justification comments |
| Docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation with `DEV_STACK_PIP_SPEC` overrides |
| Visualization | `.codeboarding/`, README Mermaid blocks | CodeBoarding CLI wrapper + per-folder sub-diagrams |
| UV Project | `pyproject.toml`, `src/<pkg>/`, `.python-version`, `uv.lock`, `tests/` | Full Python project scaffolding via `uv init --package` |
| Sphinx Docs | `docs/conf.py`, `docs/index.rst`, `docs/Makefile` | Deterministic API docs; `docs/_build/` gitignored |
| VCS Hooks | `.git/hooks/commit-msg`, `.git/hooks/pre-push`, `.dev-stack/hooks-manifest.json` | Commit linting, branch naming, signing, scope advisory, constitutional instructions |

## Entity: Pipeline Stage

Each pipeline stage row has these fields:

| Field | Values | Source of Truth |
|-------|--------|-----------------|
| Order | 1–8 | `build_pipeline_stages()` in `stages.py` |
| Name | Stage identifier | `PipelineStage.name` |
| Gate Mode | Hard / Soft | `PipelineStage.failure_mode` |
| Description | What the stage does | Stage executor function |

### Complete Pipeline (8 stages)

| # | Name | Mode | Description |
|---|------|------|-------------|
| 1 | lint | Hard gate | `ruff check` + `ruff format --check` |
| 2 | typecheck | Hard gate | `mypy` strict-mode type analysis |
| 3 | test | Hard gate | `pytest` with coverage enforcement |
| 4 | security | Hard gate | `pip-audit` + `detect-secrets` |
| 5 | docs-api | Hard gate | Deterministic Sphinx API reference build |
| 6 | docs-narrative | Soft gate | Agent-driven narrative docs in `docs/guides/` |
| 7 | infra-sync | Soft gate | Template drift detection (hooks, CI, Docker, Spec Kit) |
| 8 | commit-message | Soft gate | Agent produces structured commit narrative + trailers |

## Entity: CLI Command

### Complete CLI Command List (12 commands including version)

| Command | Description |
|---------|-------------|
| `dev-stack init [--modules ...]` | Detects repo mode (greenfield/brownfield), installs modules, scaffolds Python project (UV), writes `dev-stack.toml`, records rollback tag |
| `dev-stack update` | Refreshes managed sections or adds modules without touching user-owned content |
| `dev-stack rollback [--ref TAG]` | Restores files referenced by the last (or specified) rollback tag |
| `dev-stack mcp install\|verify` | Writes MCP server configs for the detected agent and runs health checks |
| `dev-stack pipeline run [--force]` | Executes the 8-stage pipeline with hard/soft gates |
| `dev-stack visualize [--incremental] [--depth-level N] [--no-readme] [--timeout S]` | Invokes CodeBoarding CLI for Mermaid architecture diagrams + per-folder sub-diagrams |
| `dev-stack status` | Summarizes module health, detected agent, and last pipeline run |
| `dev-stack changelog [--unreleased\|--full]` | Generates/updates `CHANGELOG.md` from conventional commit history via git-cliff |
| `dev-stack hooks status` | Shows installed hooks, expected vs actual checksums, modification status |
| `dev-stack pr [--dry-run]` | Collects branch commits, aggregates trailers, creates PR via `gh`/`glab` or prints Markdown |
| `dev-stack release [--dry-run] [--bump LEVEL] [--no-tag]` | Infers semver from conventional commits, bumps `pyproject.toml`, tags release |
| `dev-stack version` | Shows CLI version |

## Entity: Prerequisites Table

| Tool | Purpose | Required? |
|------|---------|-----------|
| Python 3.11+ | CLI runtime | Yes |
| uv | Fast virtualenv + installer | Yes |
| git 2.30+ | Rollback, conflict detection, hooks | Yes |
| Coding agent CLI | Powers docs, commit-message, visualization | Yes |
| CodeBoarding CLI | Architecture diagram generation | Optional — visualize skips |
| mypy | Static type checking | Optional — typecheck stage skips |
| sphinx | API documentation build | Optional — docs-api stage skips |
| git-cliff | Changelog rendering | Optional — `changelog` command unavailable |
| python-semantic-release | Release automation | Optional — `release` uses built-in fallback |
| gh / glab | PR creation on GitHub/GitLab | Optional — `pr` prints Markdown to stdout |

## Entity: Generated Assets Table

| Path | Purpose |
|------|---------|
| `dev-stack.toml` | Stack manifest (modules, versions, rollback tag, detected agent) |
| `pyproject.toml` + `src/<pkg>/` + `tests/` | Python project scaffolding (greenfield via UV Project module) |
| `.pre-commit-config.yaml` + `scripts/hooks/pre-commit` | Pre-commit hook that runs the 8-stage pipeline |
| `.git/hooks/commit-msg` + `.git/hooks/pre-push` | Git hooks for commit linting and branch naming enforcement |
| `.dev-stack/hooks-manifest.json` | Hook lifecycle tracking (name, checksum, timestamp) |
| `.specify/` | GitHub Spec Kit scaffold for `/speckit.*` commands |
| `.github/workflows/dev-stack-*.yml` | CI workflows for tests, deploy, vulnerability scan |
| `.claude/settings.local.json` or `.github/copilot-mcp.json` | MCP server configs for detected agent |
| `docs/conf.py`, `docs/index.rst`, `docs/Makefile` | Sphinx documentation scaffolding |
| `constitution-template.md` | Agent behavioral practices (atomic commits, TDD) |
| `.dev-stack/instructions.md` | Agent instructions for non-spec-kit workflows |
| `cliff.toml` | git-cliff config for changelog generation |
| `.codeboarding/` | CodeBoarding analysis output (Mermaid diagrams) |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation (Docker module) |
| `.dev-stack/` | Internal state directory (gitignored) |

## Relationships

```
README.md
├── Section 3 (Prerequisites) → references Entity: Prerequisites Table
├── Section 5 (Install) → references Entity: Generated Assets Table
├── Section 6 (CLI Essentials) → references Entity: CLI Command
├── Section 7 (Module Catalog) → references Entity: Module Catalog Entry
├── Section 8 (Pipeline) → references Entity: Pipeline Stage
└── Section 15 (Spec Assets) → references specs/001–004/
```
