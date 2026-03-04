# Quickstart: Init & Pipeline Enhancements

**Branch**: `002-init-pipeline-enhancements` | **Date**: 2026-02-28

---

## Prerequisites

| Tool | Version | Required | Install |
|------|---------|----------|---------|
| Python | 3.11+ | yes | `brew install python@3.12` |
| uv | 0.5+ | **yes** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.30+ | yes | `brew install git` |
| mypy | 1.10+ | recommended | Installed as dev dependency by `uv_project` module |
| sphinx | 7.0+ | recommended | Installed as optional docs dependency by `uv_project` module |
| Coding agent CLI | any | recommended | Claude CLI, GitHub Copilot CLI, or Cursor |

---

## What's New

This feature adds three enhancements:

1. **UV Project Module** — `uv init --package` scaffolding + opinionated pyproject.toml augmentation
2. **Sphinx Docs Split** — deterministic API docs (hard gate) + agent narrative docs (soft gate)
3. **Mypy Type-Checking Stage** — type checking as pipeline stage 2

The pipeline grows from 6 to 8 stages:
```
lint → typecheck → test → security → docs-api → docs-narrative → infra-sync → commit-message
```

---

## Greenfield: New Project

```bash
# Create and enter a new project directory
mkdir my-project && cd my-project
git init

# Initialize with dev-stack (all defaults)
dev-stack init

# Expected output:
#   ✓ Detected agent: claude
#   ✓ uv_project: Initialized Python project 'my_project'
#     → pyproject.toml, src/my_project/__init__.py, .python-version, uv.lock
#     → Added [tool.ruff], [tool.pytest], [tool.coverage], [tool.mypy]
#     → Added optional-deps: docs (sphinx), dev (mypy, pytest, ruff)
#     → tests/test_placeholder.py created
#   ✓ sphinx_docs: Scaffolded Sphinx configuration
#     → docs/conf.py, docs/index.rst, docs/Makefile
#     → Added docs/_build/ to .gitignore
#   ✓ hooks: Installed pre-commit hooks (8 stages)
#   ✓ speckit: Scaffolded .specify/
#   ✓ Created dev-stack.toml
#   ✓ Stack ready!
```

### Verify the project works immediately

```bash
# Run tests (should pass out of the box)
uv run pytest
# → 1 passed (test_placeholder.py)

# Run type checking
uv run --group dev mypy src/
# → Success: no issues found

# Build API docs (install docs extras first)
uv sync --group docs
cd docs && make apidoc && make html && cd ..
# → docs/_build/index.html generated

# Make a commit — full 8-stage pipeline runs
git add -A
git commit -m "initial commit"
# → lint ✓ typecheck ✓ test ✓ security ✓ docs-api ✓ ...
```

---

## Brownfield: Existing Project

```bash
cd existing-project

# Preview what would change
dev-stack init --dry-run

# Expected output:
#   Mode: brownfield
#   Conflicts detected:
#     ⚠ pyproject.toml (exists — skip-if-exists for tool sections)
#     ⚠ .gitignore (exists — will append docs/_build/ if missing)
#   New files:
#     + tests/test_placeholder.py
#     + docs/conf.py, docs/index.rst, docs/Makefile
#     + dev-stack.toml
#   Run without --dry-run to apply.

# Apply with interactive conflict resolution
dev-stack init
```

### Brownfield pyproject.toml handling

The UV Project module uses **skip-if-exists** semantics:
- Existing `[tool.ruff]` → skipped (your config preserved)
- Missing `[tool.mypy]` → added with curated defaults
- Existing `[project.optional-dependencies]` groups → skipped per-group

---

## The 8-Stage Pipeline

After initialization, every `git commit` runs:

| # | Stage | Gate | What it does |
|---|-------|------|--------------|
| 1 | lint | HARD | `ruff format --check` + `ruff check` |
| 2 | typecheck | HARD | `mypy src/` (skips if mypy not installed) |
| 3 | test | HARD | `pytest` |
| 4 | security | HARD | `pip-audit` + `detect-secrets` |
| 5 | docs-api | HARD | Sphinx apidoc + build (skips if sphinx not installed) |
| 6 | docs-narrative | SOFT | Agent updates `docs/guides/` (skips if no agent) |
| 7 | infra-sync | SOFT | Hash comparison of managed files |
| 8 | commit-message | SOFT | Agent generates structured commit message |

**Hard gates** (1-5) block the commit on failure. **Soft gates** (6-8) warn but allow the commit.

---

## Updating Existing Projects

For projects initialized before this feature:

```bash
dev-stack update

# Expected output:
#   New modules available:
#     ? uv_project — Python project scaffolding via uv [Y/n]
#     ? sphinx_docs — Sphinx documentation config [Y/n]
#   
#   (User selects Y for both)
#   
#   ✓ uv_project: Augmented pyproject.toml (skip-if-exists)
#   ✓ sphinx_docs: Scaffolded docs/conf.py, docs/index.rst, docs/Makefile
#   ✓ hooks: Updated pre-commit config (added mypy hook)
#   ✓ Pipeline updated: 6 → 8 stages
```

New modules are offered interactively — never auto-installed.

---

## Project Layout After Init

```
my-project/
├── .gitignore              # Python-specific + docs/_build/
├── .python-version         # Python version pin
├── .pre-commit-config.yaml # 8-stage pre-commit hooks
├── README.md
├── pyproject.toml          # uv_build + [tool.ruff/pytest/coverage/mypy]
├── uv.lock                 # Dependency lockfile
├── dev-stack.toml          # Stack manifest
├── .specify/               # Spec Kit scaffold
├── docs/
│   ├── conf.py             # Sphinx config (src/ layout aware)
│   ├── index.rst           # Root toctree
│   ├── Makefile            # sphinx build targets
│   ├── api/                # Generated by docs-api stage
│   ├── _build/             # Build output (.gitignore-d)
│   └── guides/             # Agent narrative docs
├── src/
│   └── my_project/
│       └── __init__.py     # main() stub
└── tests/
    ├── __init__.py
    └── test_placeholder.py # Passing placeholder test
```

---

## Developer Workflow

```bash
# 1. Write code
vim src/my_project/core.py

# 2. Write tests  
vim tests/test_core.py

# 3. Commit — pipeline catches issues before they land
git add -A && git commit

# Pipeline output:
#   [1/8] lint .................. ✓ (1.2s)
#   [2/8] typecheck ............ ✓ (3.5s)
#   [3/8] test ................. ✓ (8.2s)
#   [4/8] security ............. ✓ (2.1s)
#   [5/8] docs-api ............. ✓ (4.5s)
#   [6/8] docs-narrative ....... ⚠ skipped (no agent)
#   [7/8] infra-sync ........... ✓ (0.3s)
#   [8/8] commit-message ....... ⚠ skipped (no agent)
#   ────────────────────────────────
#   Pipeline: 6 passed, 2 skipped, 0 failed
```
