# Dev-Stack Ecosystem

Spec-driven developer tooling that bootstraps any repository with pre-commit automation, MCP servers, Spec Kit integration, Docker reproducibility, and agent-powered visualization. The implementation tracks the artifacts in `specs/001-dev-stack-ecosystem/` and mirrors the workflows validated in [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md).

## Highlights

- 🔁 **Full lifecycle automation** – `dev-stack init`, `update`, `rollback`, `status`, `pipeline run`, and `visualize` cover every stage from scaffolding to observability.
- 🧠 **Agent-native** – coding agent CLIs (Claude, GitHub Copilot, Cursor) power docs+commit stages and the D2 visualization pipeline via a unified `AgentBridge`.
- 🧩 **Modular architecture** – Hooks, MCP servers, CI workflows, Docker, Spec Kit, and Visualization modules can be installed independently or as a bundle.
- 🛡️ **Brownfield-safe** – marker-delimited sections, conflict reports, and git-based rollback guarantee user content is never overwritten unexpectedly.
- 📐 **Spec-first** – GitHub Spec Kit ships alongside the CLI so `/speckit.*` commands work immediately in every initialized repo.

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
