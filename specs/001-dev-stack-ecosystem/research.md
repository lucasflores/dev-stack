# Research: Dev-Stack Ecosystem

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

All Technical Context unknowns have been resolved through research
on three reference projects and technology evaluation.

---

## R-001: Visualization Pipeline Architecture (noodles adaptation)

**Decision**: Adapt the noodles pipeline architecture, replacing its `LLMClient`
abstraction with coding agent CLI invocations.

**Rationale**: The noodles project (`unslop-xyz/noodles`) provides a proven,
production-tested pipeline for generating interactive D2 diagrams from source code.
Its architecture cleanly separates AI-dependent analysis from deterministic D2 generation,
making the AI layer swappable. The specific swap point is `llm.py` which defines
a `LLMClient` Protocol with `generate()` and `generate_async()` methods — currently
backed by `OpenAIClient` and `GeminiClient` classes. Dev-stack replaces this layer with
an `AgentBridgeClient` that shells out to the user's coding agent CLI.

**Noodles Pipeline (as-is)**:
1. `combine_src_files()` — Scans source directory, concatenates all files into a single
   text document with line numbers (`### FILE: path\n[1] line...`)
2. `generate_overview_schema()` — Sends combined text + analysis prompt to LLM via
   `client.generate()`. Prompt instructs: "Identify ONLY user-facing entry points
   (CLI commands, HTTP routes, UI components). Follow flows to outcomes. Return JSON
   with {nodes, flows}." Node types: `entry_point`, `feature_block`, `end`.
3. `get_overview_d2_diagram()` — **Deterministic** (no LLM): parses JSON schema,
   generates D2 text with shapes (oval=entry, rect=feature, diamond=end), colors,
   status tags ([added]/[updated]/[unchanged]), tooltips, and links.
4. `generate_node_schema_and_diagram()` — Per-node drill-down: extracts code context
   (files/lines + incoming/outgoing connections), sends to LLM for detailed
   internal graph. Runs concurrently via `asyncio.gather()`.
5. `get_node_d2_diagram()` — **Deterministic**: converts per-node JSON to D2 text.
6. D2 CLI (`d2 - output.svg`) renders to SVG/PNG.

**Dev-stack Pipeline (to-be)**:
1. `scanner.py` — Same as noodles `combine_src_files()`, adapted as a class.
2. `schema_gen.py` — Replaces `generate_overview_schema()`. Writes the noodles
   analysis prompt to a temp file, invokes `<agent-cli> --print "analyze this
   codebase and return JSON..."` and captures stdout. The prompt is identical
   to noodles' `_overview_prompt()`.
3. `d2_gen.py` — Same as noodles `get_overview_d2_diagram()` + `get_node_d2_diagram()`.
   Pure Python, no AI dependency. Reuses noodles' shape/color/status conventions.
4. `incremental.py` — Same as noodles `_load_changed_files()` + manifest comparison.
   Tracks file hashes in `.dev-stack/viz/manifest.json`, only re-analyzes changed files.
5. D2 CLI renders to SVG (optional PNG).

**Key adaptation: Agent bridge replaces LLM client**:
- Noodles: `client = get_llm_client("gpt-4.1"); output = client.generate(system, user, json_format=True)`
- Dev-stack: `output = agent_bridge.invoke(prompt_text, json_output=True)` where
  `agent_bridge` shells out: `echo "$prompt" | claude --print --output-format json`
  or equivalent for copilot/cursor.

**Alternatives considered**:
- Build from scratch: Rejected — noodles' prompt engineering and D2 generation are
  mature and well-tested. Reimplementing would duplicate months of iteration.
- Use noodles as a dependency: Rejected — noodles is tightly coupled to OpenAI/Gemini
  (`from .llm import get_llm_client`). Forking would create maintenance burden.
  Adapting the pattern (not the code) is cleaner.

---

## R-002: Coding Agent CLI Invocation Strategy

**Decision**: Shell out to auto-detected coding agent CLI. Store the detected agent
in `dev-stack.toml` under `[agent]`. Support `claude`, `copilot`, and `cursor` as
first-class targets with a generic fallback.

**Rationale**: Each coding agent provides a CLI that accepts prompts and returns
structured output:
- `claude`: `echo "$prompt" | claude --print --output-format json` (headless, returns stdout)
- `copilot`: `gh copilot suggest --shell "$prompt"` (via GitHub CLI extension)
- `cursor`: Agent CLI mode (TBD — cursor's CLI is less mature)

The agent bridge abstraction provides a unified interface:
```python
class AgentBridge:
    def invoke(self, prompt: str, *, json_output: bool = False) -> str:
        """Send prompt to coding agent CLI, return response text."""
```

Detection order at `dev-stack init`:
1. Check `$DEV_STACK_AGENT` env var (explicit override)
2. Check `which claude` → use Claude CLI
3. Check `which gh` + `gh copilot --version` → use GitHub Copilot
4. Check `which cursor` → use Cursor CLI
5. None found → warn and skip generative stages

**Alternatives considered**:
- MCP tool calls from Python: Rejected — requires embedding an MCP client, which
  adds complexity and doesn't provide the full agent reasoning capabilities.
- Dedicated lightweight agent runner: Rejected — unnecessary abstraction layer.
  Shelling out is simpler, more transparent, and easier to debug.

---

## R-003: Stack Manifest Schema (`dev-stack.toml`)

**Decision**: TOML file at repo root. Schema leverages Python 3.11+ `tomllib` for
reading (stdlib, zero dependencies) and `tomli-w` for writing.

**Rationale**: TOML is the Python ecosystem standard for configuration (`pyproject.toml`).
Developers already understand it. It's diff-friendly, human-readable, and supported
by all major editors.

**Schema**:
```toml
[stack]
version = "0.1.0"
initialized = "2026-02-10T12:00:00Z"
last_updated = "2026-02-10T12:00:00Z"
rollback_ref = "abc123def"  # git commit SHA for rollback

[agent]
cli = "claude"             # auto-detected or user-specified
path = "/usr/local/bin/claude"

[modules]
hooks = { version = "0.1.0", installed = true }
mcp-servers = { version = "0.1.0", installed = true }
ci-workflows = { version = "0.1.0", installed = false }
docker = { version = "0.1.0", installed = true }
visualization = { version = "0.1.0", installed = false }
speckit = { version = "0.1.0", installed = true }

[modules.hooks.config]
stages = ["lint", "test", "security", "docs", "infra-sync", "commit-message"]
parallel_threshold = 500  # files count above which stages 1-3 parallelize

[modules.mcp-servers.config]
servers = ["context7", "github", "sequential-thinking", "huggingface", "notebooklm"]
config_location = ".vscode/mcp.json"  # or ".claude/" depending on detected agent

[modules.visualization.config]
output_dir = ".dev-stack/viz"
d2_bin = "d2"  # or absolute path
```

**Alternatives considered**:
- YAML: Rejected — more complex parsing rules, less alignment with Python ecosystem.
- JSON: Rejected — no comments, less readable for humans.
- `pyproject.toml` `[tool.dev-stack]`: Rejected — couples to Python projects only;
  dev-stack should work with any language's repo.

---

## R-004: Brownfield Conflict Detection & Marker System

**Decision**: Use deterministic marker comments for stack-managed file sections.
Format: `# === DEV-STACK:BEGIN:<section-id> ===` / `# === DEV-STACK:END:<section-id> ===`.
Detect conflicts via file-hash comparison before writing.

**Rationale**: This is the same pattern used by many configuration management tools.
Marker comments are language-agnostic (use the file's comment syntax — `#` for Python/YAML,
`//` for JS/TS, `<!-- -->` for HTML/XML). The system:
1. Before writing, hash existing file content and compare with the last known hash
   stored in `.dev-stack/state/file-hashes.json`.
2. If hash matches → safe to update stack-managed sections between markers.
3. If hash differs → user modified file → present diff and ask for consent.
4. New files (no existing) → write without prompting.

**Alternatives considered**:
- Full git-based merging: Rejected for per-file operations — too heavy.
  Git-based approach is used for rollback (whole-operation level) not per-section.
- AST-based merging: Rejected — language-specific, fragile across updates.

---

## R-005: Git-based Rollback Mechanism

**Decision**: Before each `init` or `update`, create a lightweight git tag
(`dev-stack/rollback/<timestamp>`) pointing to the current HEAD. Store the tag name
in `dev-stack.toml` under `[stack].rollback_ref`. The `dev-stack rollback` command
restores to this point via `git checkout <ref> -- .` for tracked files.

**Rationale**: Git is already present (prerequisite). Tags are lightweight, visible
in `git log --tags`, and don't pollute branch history the way auto-commits would.
Using `git stash` was considered but stashes are local-only and can be lost.

**Rollback flow**:
1. `dev-stack init` / `update` starts
2. Create tag: `git tag dev-stack/rollback/20260210T120000`
3. Record in `dev-stack.toml`: `rollback_ref = "dev-stack/rollback/20260210T120000"`
4. Perform operation
5. If user runs `dev-stack rollback`:
   - Read `rollback_ref` from `dev-stack.toml`
   - Run `git checkout <ref> -- .` to restore all files
   - Delete the tag

**Alternatives considered**:
- Auto-commit: Rejected — pollutes git history with "pre-init snapshot" commits.
- File-system backup (`.dev-stack/backup/`): Rejected — duplicates git's job,
  wastes disk space, doesn't handle untracked files well.
- Reverse-patch: Rejected — fragile if user made changes between operation and rollback.

---

## R-006: Pre-Commit Pipeline Stage Execution

**Decision**: Implement pipeline as a sequential runner with stage definitions.
Stages 1-3 (lint, test, security) are "hard gates" — failure blocks commit.
Stages 4-6 (docs, infra-sync, commit-message) are "soft gates" — failure warns.
Stages 4-6 invoke the coding agent CLI via `agent_bridge`.

**Rationale**: git hooks run as shell scripts. The pre-commit hook will invoke
`dev-stack pipeline run` which orchestrates all 6 stages in Python:

```
Stage 1: lint     → subprocess: ruff check + ruff format --check
Stage 2: test     → subprocess: pytest (if tests exist)
Stage 3: security → subprocess: pip-audit + detect-secrets
Stage 4: docs     → agent_bridge.invoke(docs_prompt)
Stage 5: infra    → compare templates vs generated files, flag drift
Stage 6: commit   → agent_bridge.invoke(commit_message_prompt) → write COMMIT_EDITMSG
```

For projects >500 files, stages 1-3 run in parallel via `concurrent.futures.ProcessPoolExecutor`.

**Alternatives considered**:
- Use pre-commit framework (pre-commit.com): Rejected — locks us into their hook
  format and makes agent integration awkward. We need full control over the pipeline.
- Makefile-based: Rejected — not cross-platform, less observability.

---

## R-007: Commit Message Agent Format

**Decision**: Use git trailer format (key-value pairs after a blank line) for
machine-parseable metadata. The commit message body uses markdown-like sections.

**Rationale**: Git trailers are a standard mechanism (`git interpret-trailers`),
supported by GitHub, and parseable by coding agents via `git log --format='%(trailers)'`.

**Format**:
```
<type>(<scope>): <summary line, max 72 chars>

## Intent
<Why this change was made — business/user goal>

## Reasoning
<Design decisions, trade-offs considered>

## Scope
<Components affected: module names, file groups>

## Narrative
<3-5 sentence summary optimized for AI agent context retrieval.
Provides enough information for a future agent to understand this
commit without reading the diff.>

Spec-Ref: specs/001-dev-stack-ecosystem/spec.md
Task-Ref: tasks.md#T-003
Agent: claude-4
Pipeline: lint=pass test=pass security=pass docs=generated
```

**Alternatives considered**:
- YAML front matter: Rejected — unusual in commit messages, breaks some git tools.
- JSON block: Rejected — not human-readable in `git log`.
- Conventional Commits only: Rejected — insufficient for agent memory retrieval.

---

## R-008: MCP Server Configuration Strategy

**Decision**: Detect the active coding agent and write MCP configs to the
agent-specific standard location. Support both VS Code Copilot (`.vscode/mcp.json`)
and Claude Code (`.claude/mcp.json` or equivalent).

**Rationale**: MCP server configuration is agent-specific. Each agent reads configs
from its own location. The stack detects which agent is in use (from `dev-stack.toml`)
and writes to the correct path.

**Server configurations**:
| Server | Package/Source | Purpose |
|--------|---------------|---------|
| Context7 | `@upstash/context7-mcp` | Library documentation lookup |
| GitHub | `@modelcontextprotocol/server-github` | Repository operations |
| Sequential Thinking | `@modelcontextprotocol/server-sequentialthinking` | Structured reasoning |
| Hugging Face | `@huggingface/mcp-server` | Model discovery & inference |
| NotebookLM | Custom/TBD | Research notebook integration |

Credential handling: All servers reference environment variables per FR-036.
The stack validates env vars at `dev-stack mcp verify` time, not at write time.

**Alternatives considered**:
- Single unified MCP config: Rejected — agents expect their own locations.
- Manage MCP servers as containers: Rejected — overkill; npm/npx packages are sufficient.
