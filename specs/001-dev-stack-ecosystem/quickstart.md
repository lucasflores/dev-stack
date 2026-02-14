# Quickstart: dev-stack

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

---

## Prerequisites

| Tool | Version | Required | Install |
|------|---------|----------|---------|
| Python | 3.11+ | yes | `brew install python@3.12` |
| uv | latest | yes | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.30+ | yes | `brew install git` |
| D2 | latest | optional | `brew install d2` (for `dev-stack visualize`) |
| Coding agent CLI | any | recommended | Claude CLI, GitHub Copilot CLI, or Cursor |

---

## Installation

```bash
# Install dev-stack globally via uv
uv tool install dev-stack

# Verify
dev-stack --version
```

---

## Greenfield: New Project

```bash
# Create a new project
mkdir my-project && cd my-project
git init

# Initialize with all default modules
dev-stack init

# Expected output:
#   ✓ Detected agent: claude
#   ✓ Installed modules: hooks, speckit, mcp-servers, ci-workflows
#   ✓ Created dev-stack.toml
#   ✓ Created rollback point: dev-stack/rollback/20260210T120000Z
#   ✓ Stack ready!
```

**What happened**:
- Created `dev-stack.toml` manifest
- Installed pre-commit hooks (ruff lint, pytest, security scan, agent-powered stages)
- Scaffolded `.specify/` for Spec Kit
- Configured MCP servers for detected agent
- Added CI workflows to `.github/workflows/`

---

## Brownfield: Existing Project

```bash
cd existing-project

# Preview what would change (no modifications)
dev-stack init --dry-run

# Expected output:
#   Mode: brownfield
#   Conflicts detected:
#     ⚠ .pre-commit-config.yaml (modified — will merge with markers)
#     ⚠ pyproject.toml (modified — will add [tool.dev-stack] section)
#   New files:
#     + dev-stack.toml
#     + .github/workflows/dev-stack-pipeline.yml
#   Run without --dry-run to apply.

# Apply with conflict resolution
dev-stack init

# Interactive prompt for each conflict:
#   .pre-commit-config.yaml already exists.
#     [a] Accept proposed (wrap in markers)
#     [s] Skip (keep current)
#     [m] Merge (open diff in editor)
#   Choice: a
```

---

## Selective Module Installation

```bash
# Install only specific modules
dev-stack init --modules hooks,visualization

# Add modules later
dev-stack update --modules mcp-servers,docker
```

---

## MCP Server Setup

```bash
# Install MCP servers for your agent
dev-stack mcp install

# Set required environment variables first
export GITHUB_TOKEN=ghp_...
export HF_TOKEN=hf_...

# Verify connectivity
dev-stack mcp verify

# Expected output:
#   ✓ context7 .......... pass (210ms)
#   ✓ github ............ pass (340ms)  
#   ✓ sequential-thinking pass (150ms)
#   ✗ huggingface ....... fail (HF_TOKEN not set)
```

---

## Visualization

```bash
# Generate full codebase diagram
dev-stack visualize

# Incremental update (only re-analyze changed files)
dev-stack visualize --incremental

# Output to specific directory
dev-stack visualize --output docs/architecture --format svg

# Expected output:
#   Scanning 42 files...
#   Generating overview schema (agent: claude)...
#   Generating node diagrams (3 nodes)...
#   Rendering D2 → SVG...
#   ✓ docs/architecture/overview.svg
#   ✓ docs/architecture/auth_module.svg
#   ✓ docs/architecture/api_layer.svg
```

---

## Pipeline (Pre-commit)

The pipeline runs automatically on every commit via pre-commit hooks:

```
Stage 1: lint (ruff) .............. hard fail
Stage 2: test (pytest) ........... hard fail
Stage 3: security (pip-audit) .... hard fail
Stage 4: docs (agent) ............ soft warn
Stage 5: infra-sync (compare) .... soft warn
Stage 6: commit-msg (agent) ...... soft warn
```

Stages 4-6 require a coding agent. They are auto-skipped if no agent is configured.

---

## Rollback

```bash
# Rollback to the last known-good state
dev-stack rollback

# Rollback to a specific point
dev-stack rollback --ref dev-stack/rollback/20260210T120000Z

# List available rollback points
git tag -l "dev-stack/rollback/*"
```

---

## Status Check

```bash
dev-stack status

# Expected output:
#   dev-stack v0.1.0 (brownfield)
#   Agent: claude (available)
#   
#   Modules:
#     ✓ hooks ............ v0.1.0  healthy
#     ✓ speckit .......... v0.1.0  healthy
#     ✓ mcp-servers ...... v0.1.0  healthy
#     ✗ visualization .... v0.1.0  unhealthy (d2 CLI not found)
#   
#   Last pipeline run: 2026-02-10 12:00:00
#   Rollback available: dev-stack/rollback/20260210T120000Z
```

---

## Project Structure (After Init)

```
my-project/
├── dev-stack.toml                    # Stack manifest
├── .dev-stack/                       # Internal state (gitignored)
│   └── viz/
│       └── manifest.json             # Visualization file hashes
├── .pre-commit-config.yaml           # Pre-commit hooks
├── .specify/                         # Spec Kit scaffold
│   ├── memory/
│   │   └── constitution.md
│   └── templates/
├── .github/
│   ├── workflows/
│   │   └── dev-stack-pipeline.yml
│   └── copilot-mcp.json              # (if Copilot detected)
├── .claude/
│   └── settings.local.json           # (if Claude detected)
├── docs/
│   └── diagrams/                     # Generated visualizations
│       └── overview.svg
├── pyproject.toml
└── scripts/
    └── hooks/                        # Custom hook scripts
```

## Validation Checklist

Use the following matrix to validate the workflow end-to-end before shipping new stack updates. Each row maps directly to success criteria in the specification.

| Scenario | Commands | Success Criteria |
|----------|----------|------------------|
| Greenfield init (SC-001, SC-003) | `time dev-stack init --json` inside an empty repo | Command completes in under 5 minutes, `dev-stack.toml` exists, and `.pre-commit-config.yaml` plus `.specify/` are created. Record the observed duration next to the test log. |
| Brownfield init (SC-002) | In a repo with existing `.pre-commit-config.yaml`, run `dev-stack init --dry-run --json` | CLI emits a `conflicts` array without touching user files. No file hashes change unless operator opts in via `--force`. |
| MCP install (SC-007) | `DEV_STACK_AGENT=claude dev-stack mcp install --json` followed by `dev-stack mcp verify --json` | All configured servers show `installed=true`. Verification either passes or clearly lists missing environment variables. |
| Visualization (SC-007) | `dev-stack visualize --incremental --json` after touching a source file | Command reports `files_changed` matching edited files. When a coding agent is unavailable, the command must fail fast with `AgentUnavailableError`. |
| Status command | `dev-stack status --json` | Output lists every installed module with `healthy=true` or an actionable `issue` string. |
| Docker reproducibility (SC-010) | `docker compose build dev-stack && docker compose run --rm dev-stack dev-stack pipeline run --force` | Pipeline succeeds inside the container without installing extra dependencies on the host. Pass the build arg `DEV_STACK_PIP_SPEC` (e.g., `DEV_STACK_PIP_SPEC=./dist/dev_stack-latest.whl docker compose build dev-stack`) when validating unpublished builds. |

> 📌 **Follow-up**: publish `dev-stack` to PyPI (or your chosen package index) so future Docker validations can rely on the default `DEV_STACK_PIP_SPEC="dev-stack>=0.1.0"` without bundling a local wheel.

### Sample commands for local builds

If you are validating directly from this repository instead of an installed wheel, point `PYTHONPATH` at `src/`:

```bash
export PYTHONPATH=/Users/<you>/dev-stack/src
export DEV_STACK_AGENT=none  # Skip generative stages when no agent CLI is available

# Greenfield init smoke test
python -m dev_stack.cli.main init --json

# Brownfield conflict preview
python -m dev_stack.cli.main init --dry-run --json

# Status check
python -m dev_stack.cli.main status --json
```

> ℹ️ Generative features (visualize, docs agent, commit message agent, MCP install) require a working coding agent CLI (`claude`, `gh copilot`, or `cursor`). When the agent is missing, set `DEV_STACK_AGENT=none`; the commands above will report a clear warning instead of failing mid-run.
