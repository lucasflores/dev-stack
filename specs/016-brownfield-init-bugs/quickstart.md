# Quickstart: Verifying Brownfield Init Bug Fixes

**Feature**: 016-brownfield-init-bugs | **Date**: 2026-04-07

## Prerequisites

- Python 3.11+, `uv`, `ruff`, `git` installed
- dev-stack installed in editable mode: `uv pip install -e ".[dev]"`

## Verification Steps

### 1. Commit-Message Hook Preserves Markdown Headers (FR-001)

```bash
# Create a test commit message with markdown headers
cat > /tmp/test-commit-msg << 'EOF'
feat: add new feature

## Intent
Add brownfield support

## Reasoning
Users need brownfield init

## Scope
hooks_runner.py only

## Narrative
Single function change
# This is a git comment that should be stripped
EOF

# Run the hook directly
python -c "
from dev_stack.vcs.hooks_runner import run_commit_msg_hook
exit(run_commit_msg_hook('/tmp/test-commit-msg'))
"
# Expected: exit code 0 (pass)
```

### 2. Greenfield Classification Detects Root-Level Python (FR-002)

```bash
# Create a temp repo with root-level Python
tmpdir=$(mktemp -d)
cd "$tmpdir" && git init && uv init --package
mkdir eval && touch eval/__init__.py eval/main.py

# Run init and check classification
dev-stack init 2>&1 | grep -i "brownfield\|greenfield"
# Expected: classified as brownfield
```

### 3. APM Version Parse Handles ANSI (FR-003)

```bash
# Unit test with mocked ANSI output
python -c "
from unittest.mock import patch, MagicMock
from dev_stack.modules.apm import APMModule
from pathlib import Path

mod = APMModule(Path('.'))
result = MagicMock()
result.stdout = '\x1b[1m╭─ apm v0.8.2 ─╮\x1b[0m'
result.returncode = 0

with patch('shutil.which', return_value='/usr/bin/apm'), \
     patch('subprocess.run', return_value=result):
    ok, msg = mod._check_apm_cli()
    print(f'ok={ok}, msg={msg}')
    assert ok, f'Expected ok=True, got {msg}'
"
```

### 4. First-Commit Auto-Format (FR-007)

```bash
# Create brownfield repo with unformatted code
tmpdir=$(mktemp -d)
cd "$tmpdir" && git init
echo 'x=1;y=2;z=3' > bad_format.py
uv init --package

# Initialize dev-stack
dev-stack init --force

# Check marker exists
ls -la .dev-stack/brownfield-init
# Expected: file exists

# Make first commit — should auto-format
git add -A && git commit -m "chore: first commit"
# Expected: commit succeeds, bad_format.py is auto-formatted

# Verify marker is gone
test ! -f .dev-stack/brownfield-init && echo "Marker removed"
```

### 5. requirements.txt Migration Prompt (FR-004)

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir" && git init
echo -e "requests==2.31.0\nflask>=3.0" > requirements.txt

dev-stack init
# Expected: interactive prompt showing deps preview, asking for confirmation
```

### 6. Root Package Detection (FR-005)

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir" && git init && uv init --package
mkdir -p config utils
touch config/__init__.py utils/__init__.py

dev-stack init --force 2>&1
# Expected: output lists "config", "utils" with src/ migration guidance
```

### 7. JSON Output (FR-006)

```bash
dev-stack --json version 2>&1 | python -m json.tool
dev-stack --json status 2>&1 | python -m json.tool
# Expected: valid JSON for all commands
```

### 8. mypy Warning for Non-src Packages (FR-008)

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir" && git init && uv init --package
mkdir eval && echo 'x: int = "wrong"' > eval/__init__.py

dev-stack init --force
# Run pipeline typecheck stage
dev-stack pipeline run --stage typecheck 2>&1
# Expected: warning listing "eval" as uncovered, recommending src/ migration
```

## Running All Tests

```bash
cd /path/to/dev-stack
pytest tests/unit/test_hooks_runner.py tests/unit/test_conflict.py tests/unit/test_apm.py -v
pytest tests/integration/test_brownfield_init.py -v
```
