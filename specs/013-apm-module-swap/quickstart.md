# Quickstart: APM Module Swap Verification

**Feature**: 013-apm-module-swap

## Prerequisites

1. APM CLI installed and on PATH:
   ```bash
   apm --version
   # Expected: >= 0.8.0
   ```

2. dev-stack built from `013-apm-module-swap` branch:
   ```bash
   cd /path/to/dev-stack-013
   pip install -e .
   ```

## Verify 1: New project uses APM module by default

```bash
mkdir /tmp/test-apm-swap && cd /tmp/test-apm-swap
dev-stack init
```

**Expected**:
- `apm.yml` created at project root with 5 default MCP servers
- `apm.lock.yaml` created
- Agent-native config files created (`.claude/`, `.github/`, etc.)
- No mention of `mcp-servers` module in output

## Verify 2: CLI subcommands work

```bash
cd /tmp/test-apm-swap

# Explicit install
dev-stack apm install

# Security audit
dev-stack apm audit
dev-stack apm audit --format json
```

**Expected**:
- `apm install` reports per-server status
- `apm audit` reports clean (no findings on default servers)

## Verify 3: Legacy module still works when opted in

```bash
mkdir /tmp/test-legacy && cd /tmp/test-legacy

# Create dev-stack.toml with explicit mcp-servers
cat > dev-stack.toml << 'EOF'
[modules]
include = ["mcp-servers"]
EOF

dev-stack init
```

**Expected**:
- `mcp-servers` module runs (creates `.claude/settings.local.json`, etc.)
- Deprecation warning displayed: "Migrate to the 'apm' module..."

## Verify 4: Existing apm.yml is not overwritten

```bash
mkdir /tmp/test-existing && cd /tmp/test-existing

# Create pre-existing apm.yml
cat > apm.yml << 'EOF'
name: my-project
version: 1.0.0
dependencies:
  mcp:
    - ghcr.io/custom/my-server
EOF

dev-stack init
```

**Expected**:
- Interactive prompt: "apm.yml already exists. Choose: [skip/merge/overwrite]"
- Choosing "skip": `apm.yml` unchanged
- Choosing "merge": `ghcr.io/custom/my-server` preserved, defaults added
- Choosing "overwrite": replaced with default 5 servers

## Verify 5: APM CLI missing produces clear error

```bash
# Temporarily hide APM from PATH
PATH_BACKUP=$PATH
export PATH=$(echo $PATH | tr ':' '\n' | grep -v apm | tr '\n' ':')

mkdir /tmp/test-no-apm && cd /tmp/test-no-apm
dev-stack init 2>&1

export PATH=$PATH_BACKUP
```

**Expected**:
- Clear error: "APM CLI not found on PATH. Install APM: ..."
- Exit code 4 (`AGENT_UNAVAILABLE`)

## Verify 6: Tests pass

```bash
cd /path/to/dev-stack-013
pytest tests/unit/test_apm_module.py tests/unit/test_apm_cmd.py -v
pytest tests/contract/test_apm_contract.py -v
```

**Expected**: All tests green.
