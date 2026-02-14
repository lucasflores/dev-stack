# Agent Invocation Contract: AgentBridge

**Branch**: `001-dev-stack-ecosystem` | **Date**: 2026-02-10

---

## Overview

The `AgentBridge` is the single abstraction through which dev-stack communicates with coding agents. It replaces the direct LLM API pattern used in noodles (`LLMClient` → OpenAI/Gemini) with a subprocess-based approach that shells out to whichever coding agent CLI is installed on the developer's machine.

No API keys are managed by dev-stack. Authentication is the agent CLI's responsibility.

---

## Interface

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AgentResponse:
    """Structured response from an agent invocation."""
    success: bool
    content: str              # Raw text output from the agent
    json_data: dict | None    # Parsed JSON if json_output=True
    agent_cli: str            # Which agent was used ("claude", "copilot", etc.)
    duration_ms: int          # Wall-clock time for the invocation
    error: str | None = None  # Error message if success=False


class AgentBridge:
    """Subprocess-based bridge to coding agent CLIs.

    Detects and invokes the available coding agent on the developer's
    machine. Provides a uniform interface regardless of which agent
    is installed.
    """

    # Detection priority order
    AGENT_PRIORITY = ["claude", "gh copilot", "cursor"]

    def __init__(self, repo_root: Path, manifest: dict | None = None) -> None:
        """Initialize the agent bridge.

        Args:
            repo_root: Path to the repository root.
            manifest: Parsed dev-stack.toml, if available. Used to read
                      [agent] config and skip detection.
        """
        self.repo_root = repo_root
        self.manifest = manifest
        self._agent_cli: str | None = None
        self._agent_path: str | None = None

    def detect(self) -> str:
        """Auto-detect the available coding agent CLI.

        Detection order:
        1. $DEV_STACK_AGENT environment variable (explicit override)
        2. manifest [agent].cli (if manifest provided and valid)
        3. `claude` (check `which claude`)
        4. `gh copilot` (check `which gh` + `gh copilot --version`)
        5. `cursor` (check `which cursor`)

        Returns:
            Agent identifier string: "claude", "copilot", "cursor", or "none".

        Side effects:
            Sets self._agent_cli and self._agent_path.
        """
        ...

    def invoke(
        self,
        prompt: str,
        *,
        json_output: bool = False,
        context_files: list[Path] | None = None,
        timeout_seconds: int = 120,
        system_prompt: str | None = None,
    ) -> AgentResponse:
        """Run a prompt through the detected coding agent.

        Args:
            prompt: The prompt text to send to the agent.
            json_output: If True, instruct the agent to return JSON and
                         parse the response.
            context_files: Additional files to include as context.
                           Passed via agent-specific mechanisms.
            timeout_seconds: Maximum wall-clock time before aborting.
            system_prompt: Optional system-level instructions.

        Returns:
            AgentResponse with the agent's output.

        Raises:
            AgentUnavailableError: If no agent is detected.
            subprocess.TimeoutExpired: If timeout exceeded (wrapped in AgentResponse).
        """
        ...

    def is_available(self) -> bool:
        """Check if an agent is configured and reachable.

        Returns:
            True if a non-"none" agent is detected and the CLI responds.
        """
        ...
```

---

## Agent-Specific CLI Mappings

Each agent CLI has different flags and invocation patterns. The `AgentBridge.invoke()` method translates the uniform interface to agent-specific commands.

### Claude CLI

```bash
# Basic invocation (non-interactive, print-only)
claude --print --output-format text "<prompt>"

# With JSON output
claude --print --output-format json "<prompt>"

# With system prompt
claude --print --system-prompt "<system>" "<prompt>"

# With context files (via allowedTools or context flags)
claude --print --context "<file1>,<file2>" "<prompt>"
```

**Timeout**: Uses `--max-turns 1` to prevent multi-turn loops.

### GitHub Copilot CLI

```bash
# Basic invocation
gh copilot suggest "<prompt>"

# With explanation mode (for docs generation)
gh copilot explain "<prompt>"
```

**Limitations**:
- No native JSON output mode; parse stdout manually
- No system prompt support; prepend to user prompt
- No context file flags; include file content in prompt text

### Cursor CLI

```bash
# Basic invocation (if cursor CLI supports non-interactive mode)
cursor --prompt "<prompt>"
```

**Limitations**:
- CLI non-interactive mode availability varies
- Fallback: warn user and skip agent-dependent stages

---

## Prompt Format Conventions

All prompts sent through the `AgentBridge` follow a structured format to maximize consistency across different agent backends.

### Schema Generation Prompt (Visualization)

Adapted from noodles' `_overview_prompt()`:

```text
You are analyzing a codebase to generate a structured architecture diagram.

Given these source files:
{combined_source}

Identify ONLY user-facing, interactive entry points (APIs, CLI commands,
UI routes) and the feature blocks they connect to.

Return JSON only with top-level keys: nodes, flows.

nodes: array of {id, type, name, description, files}
  - type: "entry_point" | "feature_block" | "end"
  - files: array of {file, lines: [start, end]}

flows: array of {from, to, description}

Rules:
- Entry points: real user-facing interactions only
- Feature blocks: coherent functional units (not individual files)  
- Every node must participate in at least one flow
- No orphan nodes
```

### Commit Message Prompt

```text
You are generating a structured commit message for the following changes.

Diff:
{git_diff}

Staged files: {file_list}

Generate a commit message with:
1. type(scope): summary (max 72 chars)
2. Blank line
3. Body paragraphs:
   - Intent: why this change was made
   - Reasoning: key design decisions  
   - Scope: affected components
   - Narrative: 3-5 sentence AI-optimized summary

4. Trailers:
   Spec-Ref: {spec_path if available}
   Task-Ref: {task_id if available}
   Agent: {agent_cli}
   Pipeline: {stage_results}

Return the commit message as plain text, ready for `git commit -m`.
```

### Documentation Update Prompt

```text
Given the following code changes:
{diff}

And the existing documentation:
{existing_docs}

Update the documentation to reflect these changes.
Preserve the existing structure and tone.
Only modify sections affected by the code changes.
Return the full updated documentation.
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No agent detected | Return `AgentResponse(success=False, agent_cli="none", error="...")` |
| Agent CLI exits non-zero | Return `AgentResponse(success=False, content=stderr, ...)` |
| Timeout exceeded | Return `AgentResponse(success=False, error="Timeout after {n}s")` |
| JSON parse failure | Return `AgentResponse(success=True, json_data=None, content=raw_output)` |
| Agent returns empty | Return `AgentResponse(success=False, error="Empty response")` |

Pipeline stages that require an agent check `AgentBridge.is_available()` first and skip with `StageResult(status="skip", skipped_reason="no agent configured")` if unavailable.

---

## Testing Seam

For unit tests, the `AgentBridge` accepts an optional `_executor` callable:

```python
def __init__(self, repo_root, manifest=None, *, _executor=None):
    self._executor = _executor or subprocess.run
```

Tests inject a mock executor that returns predefined `CompletedProcess` objects, avoiding real agent invocations.
