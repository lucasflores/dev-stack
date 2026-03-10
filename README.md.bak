
# Dev-Stack Ecosystem

> Spec-driven automation that bootstraps any repository with hooks, MCP servers, Docker reproducibility, and infra-console styled visualization — powered by coding agent CLIs.

- [What Is Dev-Stack?](#what-is-dev-stack)
- [Key Capabilities](#key-capabilities)
- [Quickstart](#quickstart)
- [CLI Essentials](#cli-essentials)
- [Module Catalog](#module-catalog)
- [Automation Pipeline](#automation-pipeline)
- [Visualization Workflow](#visualization-workflow)
- [Validation Checklist](#validation-checklist)
- [Repository Map](#repository-map)
- [Development Workflow](#development-workflow)
- [Spec Assets](#spec-assets)

## What Is Dev-Stack?

Dev-Stack is a Python 3.11+ CLI that turns any repository into a fully automated, AI-ready workspace. The CLI mirrors the artifacts inside [specs/001-dev-stack-ecosystem](specs/001-dev-stack-ecosystem) and wires together:

- Pre-commit hooks that run a six-stage automation pipeline
- GitHub Spec Kit scaffolding so `/speckit.*` commands run on day one
- MCP server provisioning for Claude, GitHub Copilot, or Cursor
- Docker + CI templates for reproducible validation
- Agent-native visualization driven by a deterministic D2 generator

## Key Capabilities

- 🔁 **Lifecycle coverage** — `init`, `update`, `rollback`, `status`, `pipeline run`, and `visualize` keep repos aligned from scaffold to observability.
- 🧠 **Agent-native execution** — `AgentBridge` shells out to detected CLIs (Claude, Copilot, Cursor) for docs, commit messages, and diagrams.
- 🧩 **Composable modules** — Install hooks, MCP servers, Spec Kit, CI, Docker, and Visualization individually or as a curated bundle.
- 🛡️ **Brownfield-safe** — Marker-delimited sections, conflict reports, and git-based rollback prevent accidental overwrites.
- 📐 **Spec-first** — Every change traces back to spec, plan, contracts, and tasks in the `specs/001-dev-stack-ecosystem` tree.

## Quickstart

| Tool | Purpose |
|------|---------|
| Python 3.11+ | CLI runtime |
| uv | Fast virtualenv + installer |
| git 2.30+ | Conflict detection + rollback |
| d2 (optional) | Renders generated D2 diagrams |
| Coding agent CLI | Powers docs, commit message, visualization |

```bash
# Install local prerequisites
brew install python@3.12 uv git d2

# Clone + editable install
git clone https://github.com/<you>/dev-stack.git
cd dev-stack
uv tool install -r pyproject.toml --link-mode=editable

# Smoke test (skip agent-dependent stages)
PYTHONPATH=src DEV_STACK_AGENT=none python -m dev_stack.cli.main --help
```

## Install Dev-Stack In Your Repo

> This flow is for consumers of the CLI: install the tool once, then run it inside any repository you want to bootstrap. The PyPI release is pending; until it lands, install from the wheel generated in `dist/`.

### 1. Install the CLI globally

```bash
# (From the dev-stack source repo) build artifacts if needed
uv build

# Install the CLI from the local wheel
uv tool install ./dist/dev_stack-0.1.0-py3-none-any.whl

# Verify it is on your PATH
dev-stack --version
```

🤝 Once the package is published to PyPI you can replace the wheel path with `uv tool install dev-stack`.

### 2. Bootstrap a repository in-place

```bash
cd /path/to/your-repo
git init  # or ensure an existing repo is clean

# Let dev-stack detect the agent and scaffold everything
dev-stack init --json

# Optional safety checks
dev-stack init --dry-run --json   # brownfield preview
dev-stack status --json           # confirm module health
```

- Set `DEV_STACK_AGENT=<cli>` if the auto-detect order (`claude → gh copilot → cursor → none`) should be overridden.
- Pass `--modules hooks,visualization` (or any subset) to control what gets installed.

### 3. Review the generated assets

| Path | Purpose |
|------|---------|
| `dev-stack.toml` | Stack manifest (modules, versions, rollback tag, detected agent) |
| `.pre-commit-config.yaml` + `scripts/hooks/pre-commit` | Pre-commit hook that runs the six-stage automation pipeline |
| `.specify/` | GitHub Spec Kit scaffold so `/speckit.*` commands work immediately |
| `.github/workflows/dev-stack-*.yml` | CI workflows for tests, deploy, vulnerability scan |
| `.claude/settings.local.json` or `.github/copilot-mcp.json` | MCP server configs targeted to the detected agent |
| `.dev-stack/` | Internal state (visualization manifests, cache) — ignored by git |
| `docs/diagrams/overview.svg` (plus per-node SVGs) | Agent-generated architecture diagrams |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation environment when the Docker module is selected |

At this point commit the changes, run `dev-stack pipeline run --force` to prime the hooks, and keep the validation checklist handy for future releases.

## CLI Essentials

| Command | What it does |
|---------|--------------|
| `dev-stack init [--modules ...]` | Detects repo mode (greenfield/brownfield), installs modules, writes `dev-stack.toml`, and records rollback tag |
| `dev-stack update` | Refreshes managed sections or adds modules without touching user-owned content |
| `dev-stack rollback [--ref TAG]` | Restores files referenced by the last (or specified) rollback tag |
| `dev-stack mcp install|verify` | Writes MCP server configs for the detected agent and runs health checks |
| `dev-stack pipeline run [--force]` | Executes lint → test → security → docs → infra-sync → commit-msg stages with proper hard/soft gates |
| `dev-stack visualize [--incremental]` | Generates noodles-inspired diagrams via agent schema + deterministic D2 rendering |
| `dev-stack status` | Summarizes module health, detected agent, and last pipeline run |

All commands support `--json`; mutating commands honor `--dry-run` before making changes.

## Module Catalog

| Module | Managed assets | Highlights |
|--------|----------------|------------|
| Hooks | `.pre-commit-config.yaml`, `scripts/hooks/*` | Six-stage automation pipeline wired into git hooks |
| Spec Kit | `.specify/` scaffold | Ships constitution, memory, templates, and scripts |
| MCP Servers | `.claude/` or `.github/` configs | Auto-installs Context7, GitHub, Sequential Thinking, Hugging Face, NotebookLM servers |
| CI Workflows | `.github/workflows/dev-stack-*.yml` | Opinionated multi-job CI with justification comments |
| Docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation with `DEV_STACK_PIP_SPEC` overrides |
| Visualization | `.dev-stack/viz/`, `docs/diagrams/*` | Infra-console D2 template + incremental regeneration |

Dependencies are resolved automatically; visualization auto-adds Hooks when required.

## Automation Pipeline

| Stage | Mode | Description |
|-------|------|-------------|
| 1. lint | Hard gate | `ruff check` + `ruff format --check` |
| 2. test | Hard gate | `pytest` (coverage enforced via `--cov-fail-under=80`) |
| 3. security | Hard gate | `pip-audit` + `detect-secrets` |
| 4. docs | Soft gate | Agent updates docs via prompt template |
| 5. infra-sync | Soft gate | Template drift detection (hooks, CI, Docker, Spec Kit) |
| 6. commit-message | Soft gate | Agent produces structured commit narrative + trailers |

Stages 1-3 parallelize automatically for repos with >500 files. Agent-dependent stages skip gracefully when `AgentBridge` cannot detect a CLI.

## Visualization Workflow

1. **Scan** — `src/dev_stack/visualization/scanner.py` concatenates files with noodles-style headers while respecting `.gitignore`.
2. **Schema** — `schema_gen.py` shells out to the coding agent using the noodles overview prompt and captures JSON `{nodes, flows}`.
3. **Generate D2** — `d2_gen.py` converts schema to infra-console themed D2 markup with status-aware classes.
4. **Render** — `visualize_cmd.py` runs the `d2` CLI (SVG/PNG) and records file hashes in `.dev-stack/viz/manifest.json` for incremental runs.

If the agent fails, dev-stack surfaces the cached diagram and reports `AgentUnavailableError` without blocking commit hooks.

## Validation Checklist

Before publishing new stack artifacts, run the full matrix in [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md#validation-checklist):

1. **Greenfield init** — `time dev-stack init --json` inside an empty repo; confirm `.specify/`, `.pre-commit-config.yaml`, and `dev-stack.toml` exist.
2. **Brownfield init** — `dev-stack init --dry-run --json` in an overlapping repo to inspect emitted `conflicts`.
3. **MCP install/verify** — `DEV_STACK_AGENT=claude dev-stack mcp install --json && dev-stack mcp verify --json` must show all servers installed or list missing env vars.
4. **Visualization** — Touch a file, run `dev-stack visualize --incremental --json`, and verify `files_changed` matches the edits.
5. **Status** — `dev-stack status --json` lists every module with `healthy=true` or a concrete issue.
6. **Docker reproducibility** — `DEV_STACK_PIP_SPEC=./dist/dev_stack-latest.whl docker compose build dev-stack && docker compose run --rm dev-stack dev-stack pipeline run --force` succeeds without extra host deps.

📌 **Follow-up**: Publish `dev-stack` to PyPI so Docker validations can rely on `DEV_STACK_PIP_SPEC="dev-stack>=0.1.0"` instead of bundling local wheels.

## Repository Map

```
dev-stack/
├── src/dev_stack/            # CLI commands, modules, pipeline, visualization, brownfield helpers
├── templates/                # Hooks, CI, Docker, MCP, Spec Kit, visualization templates
├── tests/                    # unit/, integration/, contract/ suites
├── specs/001-dev-stack-ecosystem/
│   ├── plan.md               # Implementation plan
│   ├── research.md           # Reference investigations
│   ├── data-model.md         # Entities + relationships
│   ├── quickstart.md         # Operator playbook + validation matrix
│   ├── contracts/            # CLI, module, agent contracts
│   └── tasks.md              # Phase-by-phase execution plan
├── .specify/                 # GitHub Spec Kit scaffold
├── .dev-stack/               # Internal state (viz manifests, cache)
└── dist/                     # Wheels for Docker validation
```

## Development Workflow

```bash
# Formatting + lint
uv run ruff format
uv run ruff check

# Full test suite (unit + integration + contract)
uv run pytest --override-ini addopts='' tests

# Diagram generation (requires agent + d2)
dev-stack visualize --json
```

Before merging, rerun the validation checklist to keep Docker, MCP, and visualization stages green.

## Spec Assets

- Specification: [specs/001-dev-stack-ecosystem/spec.md](specs/001-dev-stack-ecosystem/spec.md)
- Plan: [specs/001-dev-stack-ecosystem/plan.md](specs/001-dev-stack-ecosystem/plan.md)
- Data model: [specs/001-dev-stack-ecosystem/data-model.md](specs/001-dev-stack-ecosystem/data-model.md)
- Contracts: [specs/001-dev-stack-ecosystem/contracts](specs/001-dev-stack-ecosystem/contracts)
- Tasks: [specs/001-dev-stack-ecosystem/tasks.md](specs/001-dev-stack-ecosystem/tasks.md)
- Quickstart + validation: [specs/001-dev-stack-ecosystem/quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md)

Need to regenerate specs or tasks? Run `/speckit.plan`, `/speckit.specify`, and `/speckit.tasks` from the repo root to keep documentation in sync.

## Requirements

| Tool | Purpose |
|------|---------|
| Python 3.11+ | CLI runtime and packaging |
| uv | Fast virtualenv + installer for end users |
| git 2.30+ | Rollback + conflict detection |
| d2 (optional) | Render diagrams from generated D2 files |
| Coding agent CLI | Powers docs, commit-message, and visualize stages |

## Getting Started

```bash
# Install dependencies
brew install python@3.12 uv git d2

# Clone and install locally
git clone https://github.com/<you>/dev-stack.git
cd dev-stack
uv tool install -r pyproject.toml --link-mode=editable

# Smoke test
PYTHONPATH=src DEV_STACK_AGENT=none python -m dev_stack.cli.main --help
```

## Core CLI Commands

| Command | Description |
|---------|-------------|
| `dev-stack init [--modules ...]` | Scaffold a repo (greenfield or brownfield) with selected modules, create `dev-stack.toml`, and detect the coding agent |
| `dev-stack update` | Refresh managed sections or add new modules without overwriting user content |
| `dev-stack rollback [--ref TAG]` | Restore the repo to the last rollback tag recorded in the manifest |
| `dev-stack mcp install|verify` | Configure and health-check MCP servers for the detected agent |
| `dev-stack pipeline run [--force]` | Execute the 6-stage pre-commit pipeline (lint, test, security, docs, infra-sync, commit-msg) |
| `dev-stack visualize [--incremental]` | Generate noodles-inspired diagrams via the agent-driven schema + deterministic D2 generator |
| `dev-stack status` | Summarize module health, agent availability, and last pipeline run |

All commands support `--json` for automation workflows and honor `--dry-run` where destructive changes could occur.

## Validation Workflow

Follow the checklist in [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md#validation-checklist) before shipping new stack updates:

1. **Greenfield init** – `time dev-stack init --json` inside an empty repo and confirm `.pre-commit-config.yaml`, `.specify/`, and `dev-stack.toml` exist.
2. **Brownfield init** – Run `dev-stack init --dry-run --json` inside a repo with overlapping files and review the emitted `conflicts` array before applying.
3. **MCP install/verify** – `DEV_STACK_AGENT=claude dev-stack mcp install --json` followed by `dev-stack mcp verify --json` to ensure all servers report `installed=true`.
4. **Visualization** – Touch a repo file and run `dev-stack visualize --incremental --json`; `files_changed` must match the edited files and agent failures return `AgentUnavailableError`.
5. **Status** – `dev-stack status --json` should list every module with `healthy=true` or an actionable issue.
6. **Docker reproducibility** – `DEV_STACK_PIP_SPEC=./dist/dev_stack-latest.whl docker compose build dev-stack && docker compose run --rm dev-stack dev-stack pipeline run --force` must succeed without additional host deps.

📌 **Follow-up**: Publish `dev-stack` to PyPI so Docker builds can reference `DEV_STACK_PIP_SPEC="dev-stack>=0.1.0"` without bundling a local wheel.

## Architecture Snapshot

- `src/dev_stack/modules/*` – Individual capability modules implementing the `ModuleBase` contract.
- `src/dev_stack/pipeline/` – Stage definitions plus the orchestrator for lint/test/security/docs/infra/commit runs.
- `src/dev_stack/visualization/` – Scanner, schema generator, incremental diffing, and the infra-console themed D2 template.
- `src/dev_stack/brownfield/` – Conflict detection, marker utilities, and git-based rollback helpers.
- `templates/` – Vendored hook scripts, CI workflows, Docker assets, MCP server configs, and Spec Kit scaffolding.
- `tests/` – Unit, integration, and contract suites enforcing CLI schemas and module behaviors.

## Repository Layout

```
dev-stack/
├── src/dev_stack/          # CLI, modules, pipeline, visualization, brownfield helpers
├── templates/              # Hooks, CI, Docker, MCP, Spec Kit scaffolds
├── tests/                  # unit/, integration/, contract/ tiers
├── specs/001-dev-stack-ecosystem/
│   ├── plan.md             # Implementation plan
│   ├── research.md         # Technical investigations
│   ├── data-model.md       # Entities and relationships
│   ├── quickstart.md       # Validation checklist + scenarios
│   ├── contracts/          # CLI/module/agent contracts
│   └── tasks.md            # Execution plan (phases + IDs)
├── .specify/               # GitHub Spec Kit scaffold (vendored)
├── .dev-stack/             # Internal state (gitignored)
└── dist/                   # Wheels for Docker validation
```

## Development

```bash
# Format + lint + type checks
uv run ruff format
uv run ruff check

# Run full test suite
uv run pytest --override-ini addopts='' tests

# Generate diagrams (requires agent + d2)
dev-stack visualize --json
```

When opening pull requests, run the validation checklist to keep the Docker pipeline, MCP servers, and visualization stages green.

## Additional Resources

- Specification: [specs/001-dev-stack-ecosystem/spec.md](specs/001-dev-stack-ecosystem/spec.md)
- Implementation plan: [specs/001-dev-stack-ecosystem/plan.md](specs/001-dev-stack-ecosystem/plan.md)
- Contracts: [specs/001-dev-stack-ecosystem/contracts/](specs/001-dev-stack-ecosystem/contracts)
- Tasks board: [specs/001-dev-stack-ecosystem/tasks.md](specs/001-dev-stack-ecosystem/tasks.md)

Need to regenerate specs or tasks? Run `/speckit.plan`, `/speckit.specify`, and `/speckit.tasks` from the repo root to keep documentation in sync with code.
