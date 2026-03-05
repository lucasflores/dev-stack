# Quickstart: CodeBoarding Visualization

**Feature**: `003-codeboarding-viz`  
**Date**: 2026-03-04

---

## Prerequisites

1. **dev-stack** installed and initialized in your repository (`dev-stack init`)
2. **CodeBoarding CLI** installed:
   ```bash
   pip install codeboarding
   codeboarding-setup  # downloads LSP analysis binaries
   ```
3. **LLM API key** configured (CodeBoarding uses Google Gemini by default):
   ```bash
   export GOOGLE_API_KEY="your-api-key"
   ```

---

## Basic Usage

### Generate architecture diagrams

```bash
cd /path/to/your/repo
dev-stack visualize
```

This will:
1. Invoke `codeboarding --local . --depth-level 2`
2. Parse the analysis output from `.codeboarding/analysis.json`
3. Inject a top-level Mermaid diagram into `README.md`
4. Inject per-component sub-diagrams into component folder `README.md` files

### View results

Push to GitHub/GitLab — Mermaid diagrams render natively in README files.

---

## Common Flags

```bash
# Top-level diagram only (no sub-component diagrams)
dev-stack visualize --depth-level 1

# Deeper decomposition (3 levels)
dev-stack visualize --depth-level 3

# Incremental mode (only re-analyze changed files)
dev-stack visualize --incremental

# Analysis only — no README injection
dev-stack visualize --no-readme

# Custom timeout (10 minutes for large repos)
dev-stack visualize --timeout 600

# Machine-readable JSON output
dev-stack visualize --json
```

---

## Module Lifecycle

```bash
# Install visualization module
dev-stack init --modules visualization

# Check module health
dev-stack status

# Uninstall (removes dirs + managed README sections)
dev-stack init  # re-init without visualization module
```

---

## Output Structure

After running `dev-stack visualize`, the following files are created/modified:

```
<repo>/
├── .codeboarding/                     # CodeBoarding analysis output
│   ├── analysis.json                  # Component hierarchy index
│   ├── overview.md                    # Top-level architecture (Mermaid)
│   ├── <Component_Name>.md            # Per-component diagrams
│   └── injected-readmes.json          # Injection ledger (dev-stack managed)
├── README.md                          # ← Mermaid diagram injected here
└── <component-folder>/
    └── README.md                      # ← Sub-diagram injected here
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CodeBoarding CLI not found` | CLI not installed | `pip install codeboarding && codeboarding-setup` |
| CodeBoarding stderr about API keys | LLM API key not set | `export GOOGLE_API_KEY="..."` |
| Timeout after 300s | Large repo analysis | `--timeout 600` or higher |
| Empty diagrams / "no components found" | No analyzable source code | Ensure repo has Python/JS/Java/etc. source files |
| Sub-diagrams not generated | Depth level too low | Use `--depth-level 2` or higher |

---

## Development: Running from Source

```bash
# From the dev-stack repository root
cd /path/to/dev-stack
pip install -e .

# Run visualize in a target repo
cd /path/to/target-repo
dev-stack visualize --verbose
```

### Key source files

| File | Purpose |
|------|---------|
| `src/dev_stack/modules/visualization.py` | Module lifecycle (install/uninstall/verify) |
| `src/dev_stack/cli/visualize_cmd.py` | CLI command handler |
| `src/dev_stack/visualization/codeboarding_runner.py` | Subprocess invocation |
| `src/dev_stack/visualization/output_parser.py` | Parse `analysis.json` + extract Mermaid |
| `src/dev_stack/visualization/readme_injector.py` | Managed section injection + ledger |
| `src/dev_stack/visualization/incremental.py` | Manifest-based change detection (existing) |
