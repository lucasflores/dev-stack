# Dev-Stack Ecosystem

> One-command bootstrap — 9 pluggable modules, 9-stage pipeline, CodeBoarding visualization, and VCS best-practices enforcement for any Python repo.

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

## What Is Dev-Stack?

Dev-Stack is a Python 3.11+ CLI that turns any repository into a fully automated, AI-ready workspace. Run a single `dev-stack init` command and get:

- **9 pluggable modules** — Hooks, Spec Kit, MCP Servers, CI Workflows, Docker, Visualization, UV Project, Sphinx Docs, and VCS Hooks install independently or as a curated bundle
- **9-stage automation pipeline** — lint → typecheck → test → security → docs-api → docs-narrative → infra-sync → visualize → commit-message, wired into git pre-commit hooks with hard/soft gating
- **CodeBoarding visualization** — generates Mermaid architecture diagrams from source analysis and injects them into README files with managed markers
- **VCS best-practices enforcement** — conventional commit linting, configurable branch naming, SSH commit signing, PR generation, changelog automation, and semantic release
- **Python project scaffolding** — `uv init --package` bootstrapping with ruff, mypy, pytest, coverage, and Sphinx doc configuration out of the box
- **Agent-native execution** — auto-detects Claude, GitHub Copilot, or Cursor CLIs for docs generation, commit messages, and architecture diagrams
- **Brownfield safety** — marker-delimited sections, SHA-256 conflict detection, and git-based rollback prevent accidental overwrites in existing repos

The CLI mirrors the artifacts inside [specs/001-dev-stack-ecosystem](specs/001-dev-stack-ecosystem) and every subsequent spec.

## Key Capabilities

- 🧩 **Module-driven scaffolding** — 9 independently installable modules cover hooks, specs, MCP servers, CI, Docker, visualization, Python project setup, Sphinx docs, and VCS enforcement
- 🔁 **9-stage automation pipeline** — lint, typecheck, test, security, docs-api, docs-narrative, infra-sync, visualize, and commit-message stages with hard/soft gating wired into git hooks
- 📊 **CodeBoarding visualization** — generates Mermaid architecture diagrams from source analysis with `--depth-level`, `--incremental`, and per-folder sub-diagrams
- 🔒 **VCS best-practices enforcement** — conventional commit linting, configurable branch naming regex, SSH commit signing, automated PR descriptions, changelogs, and semantic releases
- 🐍 **Python project scaffolding** — `uv init --package` bootstrapping with ruff, mypy, pytest, coverage, and Sphinx pre-configured
- 🤖 **Constitutional agent instructions** — generates and injects `instructions.md` and `constitution-template.md` so coding agents follow project governance from day one
- 🛡️ **Brownfield safety** — marker-delimited managed sections, SHA-256 conflict detection, interactive resolution, and git tag–based rollback protect existing repos

## Prerequisites

| Tool | Purpose | Required? |
|------|---------|-----------|
| Python 3.11+ | CLI runtime and packaging | **Yes** |
| [uv](https://docs.astral.sh/uv/) | Fast virtualenv, installer, and project manager | **Yes** |
| git 2.30+ | Hooks, rollback, conflict detection | **Yes** |
| Coding agent CLI | Powers docs, commit-message, and visualize stages (auto-detects `claude`, `gh copilot`, or `cursor`) | **Yes** |
| [CodeBoarding](https://github.com/CodeBoarding/CodeBoarding) | Architecture diagram generation — gracefully skipped when absent | Optional |
| mypy | Type checking in the `typecheck` pipeline stage — skipped when absent | Optional |
| sphinx + sphinx-rtd-theme | API docs in the `docs-api` pipeline stage — skipped when absent | Optional |
| [git-cliff](https://git-cliff.org/) | Changelog generation via `dev-stack changelog` — warns when absent | Optional |
| [python-semantic-release](https://python-semantic-release.readthedocs.io/) | Version bumping via `dev-stack release` — warns when absent | Optional |
| gh / glab | PR auto-creation via `dev-stack pr` — falls back to stdout when absent | Optional |

## Quickstart

```bash
# Clone the repository
git clone https://github.com/<you>/dev-stack.git
cd dev-stack

# Create a virtual environment and install in editable mode
uv sync

# Smoke test — should print the CLI help
uv run dev-stack --help
```

> **Tip**: Set `DEV_STACK_AGENT=none` to skip agent-dependent pipeline stages during local development.

## Install Dev-Stack In Your Repo

> This section is for **consumers** of the CLI: install the tool once, then run it inside any repository you want to bootstrap. The PyPI release is pending; until it lands, install from the wheel in `dist/`.

### 1. Install the CLI

```bash
# Build the wheel (from the dev-stack source repo)
uv build

# Install globally via uv
uv tool install ./dist/dev_stack-0.1.0-py3-none-any.whl

# Verify it is on your PATH
dev-stack --version
```

Once the package is published to PyPI: `uv tool install dev-stack`.

### 2. Bootstrap a repository

```bash
cd /path/to/your-repo

# Greenfield — scaffold a brand-new Python project
uv init --package   # creates pyproject.toml, src/ layout, tests/
dev-stack --json init
git add -A && git commit -m "chore: initial dev-stack setup"

# Brownfield — augment an existing repo (safe conflict detection)
dev-stack --json init --dry-run   # preview what will change
dev-stack --json init             # apply
```

- The first commit after `dev-stack init` passes all pre-commit hooks automatically — no `--no-verify` needed.
- Set `DEV_STACK_AGENT=none` to skip agent detection entirely, or `DEV_STACK_AGENT=<cli>` to override auto-detection (`claude` → `gh copilot` → `cursor`).
- Pass `--modules hooks,visualization` (or any subset) to control which modules are installed.

### 3. Review the generated assets

| Path | Purpose | Module |
|------|---------|--------|
| `dev-stack.toml` | Stack manifest — modules, versions, rollback tag, detected agent | core |
| `.pre-commit-config.yaml` | Pre-commit hook config wired to the 9-stage pipeline | hooks |
| `scripts/hooks/pre-commit` | Shell entry point for git pre-commit | hooks |
| `.git/hooks/commit-msg` | Conventional-commit linting via gitlint + custom rules | vcs_hooks |
| `.git/hooks/pre-push` | Branch naming + signing enforcement | vcs_hooks |
| `.specify/` | GitHub Spec Kit scaffold — constitution, memory, templates, scripts | speckit |
| `.dev-stack/instructions.md` | Agent instructions injected into detected agent config | vcs_hooks |
| `.specify/templates/constitution-template.md` | Baseline practices injected into speckit constitution template | vcs_hooks |
| `cliff.toml` | git-cliff configuration for changelog generation | vcs_hooks |
| `.github/workflows/dev-stack-*.yml` | CI workflows — tests, deploy, vulnerability scan | ci_workflows |
| `.claude/settings.local.json` or `.github/copilot-mcp.json` | MCP server configs for the detected agent | mcp_servers |
| `docs/conf.py`, `docs/index.rst`, `docs/Makefile` | Sphinx documentation scaffold | sphinx_docs |
| `.codeboarding/` | CodeBoarding analysis output directory | visualization |
| `.dev-stack/` | Internal state — `pipeline/` and `viz/` are gitignored; `instructions.md` and `hooks-manifest.json` are tracked | core |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation environment | docker |

Default greenfield modules (5): `uv_project`, `sphinx_docs`, `hooks`, `speckit`, `vcs_hooks`. The remaining 4 (`mcp_servers`, `ci_workflows`, `docker`, `visualization`) are opt-in via `--modules`.

After init, commit the generated files with `git add -A && git commit -m "chore: initial dev-stack setup"`. The pre-commit hooks will pass cleanly. Use the [Validation Checklist](#validation-checklist) for ongoing verification.

## CLI Essentials

| Command | What it does |
|---------|--------------|
| `dev-stack init [--modules ...]` | Detects greenfield/brownfield mode, installs modules, writes `dev-stack.toml`, records rollback tag |
| `dev-stack update [--modules ...]` | Refreshes managed sections or adds modules; detects new defaults and prompts interactively |
| `dev-stack rollback [--ref TAG]` | Restores files to the last (or specified) rollback tag and cleans up intermediate tags |
| `dev-stack mcp install\|verify` | Writes MCP server configs for the detected agent and runs health checks |
| `dev-stack pipeline run [--force]` | Executes the 9-stage pipeline: lint → typecheck → test → security → docs-api → docs-narrative → infra-sync → visualize → commit-message |
| `dev-stack visualize [--incremental] [--depth-level N] [--no-readme] [--timeout S]` | Generates Mermaid architecture diagrams via CodeBoarding and injects them into README files (also runs automatically as pipeline stage 8) |
| `dev-stack status` | Summarizes module health, detected agent, and last pipeline run |
| `dev-stack changelog [--unreleased\|--full]` | Generates or updates `CHANGELOG.md` from conventional commits via git-cliff |
| `dev-stack hooks status` | Shows managed hook status with checksum validation and signing configuration |
| `dev-stack pr [--dry-run] [--base BRANCH]` | Generates PR description from branch commits; auto-creates via `gh`/`glab` or falls back to stdout |
| `dev-stack release [--bump LEVEL] [--no-tag]` | Semantic release — infers bump from conventional commits, updates version + changelog, creates git tag |
| `dev-stack version` | Prints CLI version and configuration context |

All commands support `--json` (placed before the subcommand: `dev-stack --json <command>`) for machine-readable output. Mutating commands honor `--dry-run` before making changes.

## Module Catalog

| Module | Managed Assets | Highlights |
|--------|----------------|------------|
| **Hooks** | `.pre-commit-config.yaml`, `scripts/hooks/pre-commit` | 9-stage automation pipeline wired into git pre-commit hooks |
| **Spec Kit** | `.specify/` scaffold, `.dev-stack/bin/specify` shim | Ships constitution, memory, templates, and scripts; preserves `memory/constitution.md` on update |
| **MCP Servers** | `.claude/settings.local.json` or `.github/copilot-mcp.json` | Auto-installs Context7, GitHub, Sequential Thinking, Hugging Face, NotebookLM servers for detected agent |
| **CI Workflows** | `.github/workflows/dev-stack-{tests,deploy,vuln-scan}.yml` | Opinionated multi-job GitHub Actions CI with SHA-256 conflict detection |
| **Docker** | `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Reproducible validation with `DEV_STACK_PIP_SPEC` overrides; uv-based installation |
| **Visualization** | `.codeboarding/`, `.dev-stack/viz/` | CodeBoarding CLI → Mermaid diagram generation + managed-marker README injection; cleans up legacy `docs/diagrams/` |
| **UV Project** | `pyproject.toml`, `.python-version`, `.gitignore`, `tests/` scaffold | `uv init --package` bootstrapping with ruff, mypy, pytest, coverage, and optional-dependencies (`docs`, `dev`) pre-configured |
| **Sphinx Docs** | `docs/conf.py`, `docs/index.rst`, `docs/Makefile` | Auto-detects package name; generates docs with `-W --keep-going` flags; appends `docs/_build/` to `.gitignore` |
| **VCS Hooks** | `.git/hooks/commit-msg`, `.git/hooks/pre-push`, `.specify/templates/constitution-template.md`, `.dev-stack/instructions.md`, `cliff.toml` | Conventional commit linting (gitlint + custom rules), branch naming enforcement, SSH signing configuration, constitutional agent instructions, checksum-tracked hook manifests |

Dependencies are resolved automatically — for example, Sphinx Docs requires UV Project. Default greenfield install order: `uv_project` → `sphinx_docs` → `hooks` → `speckit` → `vcs_hooks`.

## Automation Pipeline

| # | Stage | Mode | Description |
|---|-------|------|-------------|
| 1 | lint | Hard gate | `ruff format --check .` + `ruff check .` |
| 2 | typecheck | Hard gate | `python3 -m mypy src/` — skips gracefully when mypy is not installed |
| 3 | test | Hard gate | `pytest -q` — skips when `tests/` directory is missing |
| 4 | security | Hard gate | `pip-audit` + `detect-secrets scan` |
| 5 | docs-api | Hard gate | `sphinx-apidoc` + `sphinx -b html -W --keep-going` |
| 6 | docs-narrative | Soft gate | Agent-generated narrative docs in `docs/guides/` |
| 7 | infra-sync | Soft gate | Checksums templates vs installed hooks/config for drift detection |
| 8 | visualize | Soft gate | Runs CodeBoarding analysis and injects Mermaid diagrams into READMEs — skips when CodeBoarding CLI is absent, `[tool.dev-stack.pipeline] visualize = false`, or no LLM API key is configured |
| 9 | commit-message | Soft gate | Agent-generated structured commit narrative with conventional format and required trailers (`Spec-Ref`, `Task-Ref`, `Pipeline`, etc.) — skips when user supplies `-m` message |

- **Hard gates** (stages 1–5): halt the pipeline on failure — the commit is blocked.
- **Soft gates** (stages 6–9): warn on failure but allow the commit to proceed; use `--force` to suppress warnings.
- Stages `lint`, `test`, and `security` parallelize via `ProcessPoolExecutor` in repos with >500 files.
- Agent-dependent stages (6, 9) skip gracefully when no coding agent CLI is detected.
- Stage 8 (visualize) skips when CodeBoarding is not installed or visualization is disabled via config.
- Stage 8 (visualize) requires an LLM API key. Set one of: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`, or `COHERE_API_KEY`. The stage skips gracefully with an actionable message when none are set.
- Stage 9 (commit-message) skips when the user supplies a message via `git commit -m "..."`. User-supplied messages take precedence; the stage only generates structured messages in interactive commit mode.

## Visualization Workflow

1. **Invoke** — `codeboarding_runner.py` launches the [CodeBoarding](https://github.com/CodeBoarding/CodeBoarding) CLI as a subprocess with a configurable timeout (default 300 s). Pass `--depth-level N` (default 2) to control analysis depth.
2. **Parse** — `output_parser.py` reads `.codeboarding/analysis.json`, extracts typed components and relationships, and maps each component to its target folder using longest common directory prefix.
3. **Inject** — `readme_injector.py` writes Mermaid diagram blocks into the root `README.md` (marker: `architecture`) and per-folder READMEs (marker: `component-architecture`) using brownfield managed markers. An `InjectionLedger` tracks every injection for clean removal on uninstall.

```bash
# Full regeneration
dev-stack --json visualize

# Incremental — only re-analyze if source files changed
dev-stack --json visualize --incremental

# Generate diagrams without injecting into READMEs
dev-stack --json visualize --no-readme
```

The `--incremental` flag compares SHA-256 hashes of source files against `.dev-stack/viz/manifest.json` — unchanged repos are skipped entirely.

## Validation Checklist

Run these checks after `dev-stack init` or `dev-stack update` to confirm everything is wired correctly. See [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md) for detailed scenarios.

1. **CLI responds** — `dev-stack --help` prints all 12 commands without errors.
2. **Modules healthy** — `dev-stack --json status` reports `healthy: true` for every installed module.
3. **Pipeline passes** — `dev-stack --json pipeline run --force` completes stages 1–5 (hard gates) without failure.
4. **Hooks installed** — `dev-stack --json hooks status` shows `commit-msg` and `pre-push` hooks with valid checksums.
5. **Visualization works** — `dev-stack --json visualize` produces `.codeboarding/` output and injects Mermaid diagrams into README.
6. **Config loads** — `grep 'tool.dev-stack' pyproject.toml` shows hooks, branch, and signing sections.
7. **Brownfield safe** — `dev-stack --dry-run --json init` in an existing repo lists `conflicts` without modifying files.
8. **Rollback available** — `git tag -l 'dev-stack/rollback/*'` shows at least one rollback tag (requires at least one commit before `dev-stack init`).

## Configuration

Dev-Stack reads its configuration from `[tool.dev-stack.*]` tables in `pyproject.toml`:

```toml
[tool.dev-stack.hooks]
commit-msg = true       # Conventional-commit linting via gitlint + custom rules
pre-push = true         # Branch naming + signing enforcement
pre-commit = true       # Lint + typecheck on staged files

[tool.dev-stack.branch]
pattern = "^(main|master|develop|feature/.+|bugfix/.+|hotfix/.+|release/.+|\\d{3}-.+)$"
exempt = ["main", "master"]

[tool.dev-stack.signing]
enabled = false         # Enable SSH commit signing
enforcement = "warn"    # "warn" (advisory) or "block" (reject unsigned commits)
key = ""                # Path to SSH public key — auto-detected from ssh-agent when empty

[tool.dev-stack.pipeline]
visualize = true        # Auto-regenerate CodeBoarding diagrams as pipeline stage 8
```

- **Branch naming** — The `pre-push` hook validates the current branch against the configured regex pattern. Branches in the `exempt` list are always allowed.
- **Hook selection** — Enable or disable individual hooks. Disabled hooks are not installed; manually modified hooks are detected via checksum and skipped on update.
- **Signing** — When enabled, the `pre-push` hook verifies commits are signed with a valid SSH key. Set `enforcement = "block"` to reject unsigned pushes.
- **Scope advisory** — `dev-stack` analyzes staged files on commit and surfaces an advisory scope suggestion (e.g., `feat(pipeline):`) based on which source packages are touched.

## Repository Layout

```
dev-stack/
├── src/dev_stack/
│   ├── cli/                  # Click commands (init, update, rollback, mcp, pipeline, …)
│   ├── modules/              # 9 pluggable modules (hooks, speckit, mcp_servers, …)
│   ├── pipeline/             # 9-stage orchestrator, agent bridge, commit formatter
│   ├── brownfield/           # Conflict detection, marker utilities, rollback helpers
│   ├── vcs/                  # Commit parsing, branch validation, PR/changelog/release, signing, scope
│   ├── rules/                # Gitlint custom rules — conventional commits + trailers
│   ├── visualization/        # CodeBoarding runner, output parser, README injector, incremental diffing
│   ├── templates/            # Vendored hooks, CI, Docker, MCP, Spec Kit, and VCS templates
│   ├── config.py             # Agent detection + manifest loading
│   ├── errors.py             # Structured error hierarchy
│   └── manifest.py           # dev-stack.toml reader/writer
├── tests/
│   ├── unit/                 # Fast isolated tests for every module and package
│   ├── integration/          # End-to-end flows (init, update, rollback, visualize, …)
│   └── contract/             # CLI schema + module interface contracts
├── specs/
│   ├── 001-dev-stack-ecosystem/
│   ├── 002-init-pipeline-enhancements/
│   ├── 003-codeboarding-viz/
│   ├── 004-vcs-best-practices/
│   └── 005-readme-update/
├── .specify/                 # GitHub Spec Kit scaffold (vendored)
├── .dev-stack/               # Internal state — viz manifests, pipeline cache (gitignored)
├── pyproject.toml            # Package metadata, dependencies, tool config
└── dist/                     # Built wheels for Docker validation
```

## Architecture Snapshot

- **`src/dev_stack/cli/`** — Click-based CLI with 12 commands, global `--json`/`--dry-run`/`--verbose` flags, and structured exit codes.
- **`src/dev_stack/modules/`** — 9 pluggable modules implementing the `ModuleBase` contract (`install`, `verify`, `uninstall`); dependency resolution ensures correct ordering.
- **`src/dev_stack/pipeline/`** — 9-stage orchestrator with hard/soft gating, `ProcessPoolExecutor` parallelization, `AgentBridge` for coding-agent invocation, and last-run state persistence.
- **`src/dev_stack/brownfield/`** — Conflict detection via SHA-256 checksums, marker-delimited managed sections, interactive resolution prompts, and git tag–based rollback.
- **`src/dev_stack/vcs/`** — Commit parsing (`git log` → typed `CommitSummary`), branch validation against configurable regex, PR description generation with AI/human stats, changelog via git-cliff, semantic release with version bumping, SSH signing configuration, and scope advisory analysis.
- **`src/dev_stack/rules/`** — Custom gitlint rules: `ConventionalCommitRule` (validates `type(scope): description`), `TrailerPresenceRule` + `TrailerPathRule` (enforce required trailers on agent commits), and `PipelineFailureWarningRule` (non-blocking warnings for failed stages).
- **`src/dev_stack/visualization/`** — CodeBoarding CLI runner with timeout management, `.codeboarding/analysis.json` parser that extracts Mermaid diagrams, README injector with managed markers and ledger tracking, and incremental diffing via SHA-256 file manifests.
- **`src/dev_stack/templates/`** — Vendored hook scripts, CI workflows, Docker assets, MCP server configs (Claude + Copilot), Spec Kit scaffolding, and VCS templates (cliff.toml, constitution, instructions, PR template).
- **`tests/`** — Unit, integration, and contract suites enforcing CLI schemas, module behaviors, and pipeline correctness.

## Development

```bash
# Format + lint
uv run ruff format
uv run ruff check

# Type checking
uv run mypy src/

# Full test suite (unit + integration + contract)
uv run pytest --override-ini addopts='' tests

# Generate architecture diagrams
dev-stack --json visualize
```

Before merging, rerun the [Validation Checklist](#validation-checklist) to keep hooks, pipeline, and visualization in sync.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `detect-secrets` reports findings in `.dev-stack/` files | Baseline generated without `--exclude-files` (pre-007 installs) | Delete `.secrets.baseline` and re-run `dev-stack init` to regenerate with exclusions |
| `dev-stack init` requires `--force` after `uv init --package` | Predecessor files detected as conflicts (pre-007 behavior) | Update dev-stack and re-run `dev-stack init` — predecessor files are now auto-resolved |
| `DEV_STACK_AGENT=none` still detects an agent | Agent override bug (pre-007) | Update dev-stack — `none` is now recognized as a sentinel value |
| `constitution-template.md` at repo root instead of `.specify/templates/` | Old install placement (pre-007) | Re-run `dev-stack init` — the file will be migrated automatically |
| Pre-commit hooks fail on the very first commit | Rare edge case with external baseline tools | Use `git commit --no-verify -m "chore: initial setup"` as a one-time fallback, then fix the underlying issue |

## Spec Assets

- **001 — Dev-Stack Ecosystem** (initial scaffold)
  - [spec.md](specs/001-dev-stack-ecosystem/spec.md) · [plan.md](specs/001-dev-stack-ecosystem/plan.md) · [data-model.md](specs/001-dev-stack-ecosystem/data-model.md) · [contracts/](specs/001-dev-stack-ecosystem/contracts) · [tasks.md](specs/001-dev-stack-ecosystem/tasks.md) · [quickstart.md](specs/001-dev-stack-ecosystem/quickstart.md)
- **002 — Init Pipeline Enhancements** (UV Project, Sphinx Docs, 8-stage pipeline)
  - [spec.md](specs/002-init-pipeline-enhancements/spec.md) · [plan.md](specs/002-init-pipeline-enhancements/plan.md) · [data-model.md](specs/002-init-pipeline-enhancements/data-model.md) · [tasks.md](specs/002-init-pipeline-enhancements/tasks.md)
- **003 — CodeBoarding Visualization** (CodeBoarding + Mermaid diagram generation)
  - [spec.md](specs/003-codeboarding-viz/spec.md) · [plan.md](specs/003-codeboarding-viz/plan.md) · [data-model.md](specs/003-codeboarding-viz/data-model.md) · [tasks.md](specs/003-codeboarding-viz/tasks.md)
- **004 — VCS Best Practices** (commit linting, branch naming, signing, PR/changelog/release)
  - [spec.md](specs/004-vcs-best-practices/spec.md) · [plan.md](specs/004-vcs-best-practices/plan.md) · [data-model.md](specs/004-vcs-best-practices/data-model.md) · [tasks.md](specs/004-vcs-best-practices/tasks.md)

Need to regenerate specs or tasks? Run `/speckit.plan`, `/speckit.specify`, and `/speckit.tasks` from the repo root.
