# Contract: Agent Sandbox Mode

**Module affected**: `src/dev_stack/pipeline/agent_bridge.py`

## Updated: `AgentBridge.invoke()` Signature

**Current**:
```python
def invoke(self, prompt: str, ...) -> AgentResponse:
```

**New**:
```python
def invoke(self, prompt: str, ..., sandbox: bool = False) -> AgentResponse:
```

When `sandbox=True`, the command builder MUST enforce read-only access.

## Updated: `_build_command()` — Copilot

**Current** (line ~207–228):
```python
env["COPILOT_ALLOW_ALL"] = "true"
cmd.extend(["--allow-all"])
```

**New** (when `sandbox=True`):
```python
# Do NOT set COPILOT_ALLOW_ALL
cmd.extend([
    "--deny-tool='write'",
    "--allow-tool='read_file'",
    "--allow-tool='grep_search'",
    "--allow-tool='file_search'",
    "--allow-tool='semantic_search'",
    "--allow-tool='list_dir'",
])
```

When `sandbox=False` (default), behavior is unchanged.

## Updated: `_build_command()` — Claude

**Current**: Uses `--print --max-turns 1`

**New** (when `sandbox=True`): Add `--disallowedTools` with write operations.

```python
if sandbox:
    cmd.extend(["--disallowedTools", "Edit,Write,Bash"])
```

When `sandbox=False`, behavior is unchanged.

## Updated: `_build_command()` — Cursor

**Current**: Uses `cursor --prompt -` (stdin-based prompt)

**New** (when `sandbox=True`): Cursor CLI uses the same `--disallowedTools` flag interface as Claude.

```python
if sandbox:
    cmd.extend(["--disallowedTools", "Edit,Write,Bash"])
```

When `sandbox=False`, behavior is unchanged. Cursor's `--prompt` mode already limits interactivity; `--disallowedTools` adds explicit write prevention.

## Decision Logic

```python
# In _execute_stage() or equivalent:
hook_context = os.environ.get("DEV_STACK_HOOK_CONTEXT")
sandbox_mode = hook_context is not None  # sandbox during any hook
response = self.agent_bridge.invoke(prompt, sandbox=sandbox_mode)
```

## Staged Content Protection

Before and after each agent invocation during sandboxed execution:

```python
if sandbox_mode:
    snapshot_before = StagedSnapshot.capture()
    response = self.agent_bridge.invoke(prompt, sandbox=True)
    snapshot_after = StagedSnapshot.capture()
    if snapshot_before.diff_hash != snapshot_after.diff_hash:
        raise StagedContentViolation(
            f"Stage {stage_name} modified staged content"
        )
```

### `StagedSnapshot.capture()` (classmethod)

```python
@classmethod
def capture(cls) -> "StagedSnapshot":
    diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout
    names = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout
    return cls(
        diff_hash=hashlib.sha256(diff.encode()).hexdigest(),
        file_list_hash=hashlib.sha256("\n".join(sorted(names.strip().splitlines())).encode()).hexdigest(),
        captured_at=time.perf_counter(),
    )
```
