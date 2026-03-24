# Quickstart: Universal Init Pipeline

**Feature**: 012-universal-init-pipeline  
**Date**: 2026-03-24

## What Changed

This feature makes `dev-stack init` work correctly on any repository, regardless of language or tech stack. Six issues are fixed:

1. **`uv sync` only runs when Python project module is selected** — No more failures on non-Python repos.
2. **`.secrets.baseline` only generated when secrets module is explicitly selected** — No stray files.
3. **Agent commit body sections are validated** — Commits with `Agent:` trailer must have Intent, Reasoning, Scope, Narrative sections.
4. **`.dev-stack/` is always gitignored** — Skip marker never appears as untracked.
5. **Hooks adapt to project stack** — Python hooks omitted on non-Python repos.
6. **No machine-specific paths in `dev-stack.toml`** — Agent CLI resolved at runtime.

## Development Setup

```bash
# Clone and checkout feature branch
git checkout 012-universal-init-pipeline

# Install in dev mode
uv sync --all-extras

# Run tests
pytest tests/ -v
```

## Testing the Changes

### Non-Python repo init

```bash
# Create a test repo with no Python files
mkdir /tmp/test-non-python && cd /tmp/test-non-python
git init
echo "# Test" > README.md
git add . && git commit -m "init: initial commit"

# Run dev-stack init without uv_project
dev-stack init --modules hooks,speckit,vcs_hooks

# Verify: no errors, clean tree, no Python hooks
git status  # Should be clean
cat .pre-commit-config.yaml  # Should NOT contain ruff/pytest/mypy
test ! -f .secrets.baseline  # File should NOT exist
grep -q ".dev-stack/" .gitignore  # Should be present
```

### Agent commit body validation

```bash
# Test rejection: agent trailer but no body sections
cat > /tmp/test-msg.txt << 'EOF'
feat: add feature

Agent: test-agent
Pipeline: lint=pass
Edited: false
Spec-Ref: none
Task-Ref: none
EOF

# Run commit-msg hook directly
python -m dev_stack.vcs.hooks_runner /tmp/test-msg.txt
# Expected: Error — missing ## Intent, ## Reasoning, ## Scope, ## Narrative

# Test acceptance: agent trailer with all body sections
cat > /tmp/test-msg.txt << 'EOF'
feat: add feature

## Intent
Add a new feature for testing.

## Reasoning
Needed for the test suite.

## Scope
tests/

## Narrative
Added a test file to validate the feature works correctly.

Agent: test-agent
Pipeline: lint=pass
Edited: false
Spec-Ref: none
Task-Ref: none
EOF

python -m dev_stack.vcs.hooks_runner /tmp/test-msg.txt
# Expected: pass
```

### Manifest portability

```bash
# After init, check dev-stack.toml
cat dev-stack.toml | grep -c "path"  # Should be 0
cat dev-stack.toml | grep "cli"      # Should show agent CLI name only
```

## Key Files to Review

| File | Change |
|------|--------|
| `src/dev_stack/cli/init_cmd.py` | Gate uv sync, gate secrets, add gitignore managed section |
| `src/dev_stack/modules/hooks.py` | Stack-aware hook generation |
| `src/dev_stack/config.py` | `detect_stack_profile()` function |
| `src/dev_stack/manifest.py` | `AgentConfig.to_dict()` drops `path` |
| `src/dev_stack/rules/body_sections.py` | New UC5 gitlint rule |
| `tests/unit/test_stack_profile.py` | Stack profile detection tests |
| `tests/unit/test_hooks_stack_aware.py` | Stack-aware hook tests |
| `tests/unit/test_body_section_rule.py` | Body section rule tests |
| `tests/unit/test_init_nonpython.py` | Non-Python init tests |
