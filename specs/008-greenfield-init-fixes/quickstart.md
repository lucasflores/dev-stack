# Quickstart: Verifying Greenfield Init Fixes

**Feature**: 008-greenfield-init-fixes
**Date**: 2026-03-10

## Prerequisites

- `uv` installed and on PATH
- `dev-stack` installed (via `uv tool install`)
- Git available

## Verification Steps

### 1. Create a fresh test repo

```bash
cd /tmp
mkdir greenfield-test && cd greenfield-test
git init
uv init --package
```

### 2. Run dev-stack init

```bash
dev-stack --json init
```

**Expected**: JSON output with `"status": "success"`, `"mode": "greenfield"`.

### 3. Verify test scaffold (FR-001)

```bash
ls tests/
# Expected output: __init__.py  test_placeholder.py

cat tests/test_placeholder.py
# Expected: valid import test for the package
```

### 4. Verify dev dependencies in pyproject.toml (FR-002)

```bash
grep -A5 '\[project.optional-dependencies\]' pyproject.toml
# Expected: [dev] group with ruff, mypy, pytest, pytest-cov
# Expected: [docs] group with sphinx, sphinx-autodoc-typehints, myst-parser
```

### 5. Verify tools installed in venv (FR-003)

```bash
.venv/bin/ruff --version
.venv/bin/mypy --version
.venv/bin/pytest --version
# Expected: all three return version strings (not "command not found")
```

### 6. Commit and verify pipeline (FR-004, FR-005)

```bash
git add -A
git commit -m "chore: initial dev-stack setup"
```

**Expected**: Pipeline runs with `lint`, `typecheck`, `test` stages showing `pass` (not `skip`).

### 7. Verify agent scoping (FR-006)

```bash
# In a new repo:
cd /tmp && mkdir agent-test && cd agent-test && git init && uv init --package
DEV_STACK_AGENT=none dev-stack --json init
git add -A
git commit -m "chore: test agent scoping"
```

**Expected**: Agent-dependent stages (docs-narrative, commit-message) show `skip` with reason `"coding agent unavailable"`, confirming the `none` setting persisted from init via `dev-stack.toml`.

### 8. Verify hollow pipeline warning (edge case)

```bash
# Simulate missing tools by removing them:
cd /tmp && mkdir hollow-test && cd hollow-test && git init && uv init --package
# Manually edit pyproject.toml to remove optional-dependencies, then:
dev-stack pipeline run
```

**Expected**: Pipeline returns `success` but includes a warning like:
```
⚠ No substantive validation: lint, typecheck, test all skipped due to missing tools.
Run 'uv sync --extra dev' to install.
```

## Cleanup

```bash
rm -rf /tmp/greenfield-test /tmp/agent-test /tmp/hollow-test
```
