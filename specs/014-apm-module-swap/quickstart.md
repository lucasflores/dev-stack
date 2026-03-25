# Quickstart: Remove SpecKit Module — Verification Guide

**Feature**: 014-apm-module-swap

## Prerequisites

1. dev-stack built from `014-apm-module-swap` branch:
   ```bash
   cd /path/to/dev-stack
   git checkout 014-apm-module-swap
   pip install -e .
   ```

2. APM CLI installed and on PATH (>= 0.8.0):
   ```bash
   apm --version
   ```

## Verify 1: SpecKit module no longer registered

```bash
python -c "from dev_stack.modules import available_modules; print(available_modules())"
```

**Expected**: Output does NOT contain `'speckit'`. Contains `'apm'`, `'hooks'`, `'uv_project'`, etc.

```bash
python -c "from dev_stack.modules import DEFAULT_GREENFIELD_MODULES; print(DEFAULT_GREENFIELD_MODULES)"
```

**Expected**: `('uv_project', 'sphinx_docs', 'hooks', 'apm', 'vcs_hooks')` — no `'speckit'`.

## Verify 2: Greenfield init works without speckit

```bash
mkdir /tmp/test-014-init && cd /tmp/test-014-init
dev-stack init
```

**Expected**:
- `apm.yml` created with both `dependencies.mcp` and `dependencies.apm` sections
- Agency reviewers and LazySpecKit are declared in `dependencies.apm`
- No speckit-related files or directories created
- No error or traceback mentioning speckit

## Verify 3: Expanded apm.yml template

```bash
cat /tmp/test-014-init/apm.yml
```

**Expected**: Contains `dependencies.apm` section with:
- `msitarzewski/agency-agents#<tag>`
- `Hacklone/lazy-spec-kit#<tag>`

And `dependencies.mcp` section with 5 MCP servers (unchanged from before).

## Verify 4: Existing project update with speckit entry

```bash
mkdir /tmp/test-014-update && cd /tmp/test-014-update

# Simulate an existing project with speckit
cat > dev-stack.toml << 'EOF'
[metadata]
version = "0.1.0"
initialized = "2026-01-01T00:00:00Z"
last_updated = "2026-01-01T00:00:00Z"
mode = "greenfield"

[modules.hooks]
version = "0.1.0"
installed = true

[modules.speckit]
version = "0.1.0"
installed = true
EOF

dev-stack update
```

**Expected**:
- Command completes with exit code 0
- Info message displayed about speckit being removed
- `dev-stack.toml` now has `deprecated = true` under `[modules.speckit]`
- No traceback or error

```bash
grep -A 5 'modules.speckit' /tmp/test-014-update/dev-stack.toml
```

**Expected**: Shows `deprecated = true` in the section.

## Verify 5: Deleted files are gone

```bash
# These should NOT exist in the source tree
ls src/dev_stack/modules/speckit.py 2>&1          # "No such file"
ls src/dev_stack/templates/speckit/ 2>&1           # "No such file"
ls src/dev_stack/templates/lazyspeckit/ 2>&1       # "No such file"
ls tests/unit/test_speckit_lazyspeckit.py 2>&1     # "No such file"
ls tests/integration/test_speckit.py 2>&1          # "No such file"
```

## Verify 6: All tests pass

```bash
cd /path/to/dev-stack
pytest tests/ -x -q
```

**Expected**: All tests pass — no failures related to speckit imports or missing modules.

## Verify 7: Post-init specify setup

```bash
cd /tmp/test-014-init
specify init --here --ai copilot
ls .specify/
```

**Expected**: `.specify/` directory created with `memory/`, `templates/`, `scripts/` subdirectories. This confirms the documented post-init step works.

## Verify 8: Project with no speckit entry updates cleanly

```bash
mkdir /tmp/test-014-clean && cd /tmp/test-014-clean

cat > dev-stack.toml << 'EOF'
[metadata]
version = "0.1.0"
initialized = "2026-01-01T00:00:00Z"
last_updated = "2026-01-01T00:00:00Z"
mode = "greenfield"

[modules.hooks]
version = "0.1.0"
installed = true

[modules.apm]
version = "0.1.0"
installed = true
EOF

dev-stack update
```

**Expected**: No migration message — update proceeds normally without mentioning speckit.
