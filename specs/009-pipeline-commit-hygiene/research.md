# Research: Pipeline Commit Hygiene

**Feature Branch**: `009-pipeline-commit-hygiene`
**Date**: 2026-03-10

## R1: Auto-Staging Pipeline Outputs Within a Pre-Commit Hook

**Task**: Research whether `git add` of specific paths within a pre-commit hook is safe and supported by git.

### Decision: `git add` in pre-commit hooks is safe for pipeline-generated files

**Rationale**:
- Git's pre-commit hook runs *before* the commit message is finalized. The hook has full access to the index and can modify it via `git add` or `git rm`.
- The `pre-commit` framework itself uses this pattern — many hooks (e.g., `black`, `isort`, `prettier`) reformat files and the framework auto-stages the changes.
- The key constraint: `git add` must target specific known paths, not `git add -A` (which could pull in unrelated working tree changes).
- Git's index lock (`index.lock`) is held during the commit flow but `git add` of specific files works correctly because it modifies the index in-place.

**Alternatives considered**:
- **Working-tree snapshot/restore**: Take a `git stash` before running the pipeline, then `git stash pop` after. Rejected: overly complex, doesn't solve the timestamp rewrite problem, and risks data loss.
- **Post-commit fixup**: Auto-commit pipeline outputs in a separate commit after the user's commit. Rejected: pollutes commit history with mechanical fixup commits.
- **Pre-commit framework auto-staging**: Rely on `pre-commit` framework's built-in file staging. Rejected: dev-stack uses a direct bash hook (`scripts/hooks/pre-commit`), not the `pre-commit` framework for the main pipeline flow.

**Implementation approach**:
- After all pipeline stages complete in `PipelineRunner.run()`, collect output paths from stages that reported "pass" or "skip".
- Run `git add <paths>` for each path that exists on disk and is not gitignored.
- Only auto-stage when running in pre-commit context (detected via `GIT_INDEX_FILE` environment variable, which git sets when a hook is executing).

## R2: Detecting Pre-Commit Hook Context vs Standalone

**Task**: Research how to reliably detect whether the pipeline is running inside a git pre-commit hook.

### Decision: Check for `GIT_INDEX_FILE` environment variable

**Rationale**:
- When git runs a hook, it sets `GIT_INDEX_FILE` to point to the index file (usually `.git/index`). This variable is NOT set during normal CLI invocations.
- Alternative: `GIT_EXEC_PATH` or checking parent process. Both are less reliable.
- The `pre-commit` framework uses a similar technique (checking `PRE_COMMIT=1` env var it sets itself).
- Most robust approach: set a `DEV_STACK_HOOK_CONTEXT=pre-commit` env var in the bash hook script, and check for it in the runner.

**Alternatives considered**:
- **`GIT_INDEX_FILE` check only**: Works but is set by git for ALL hooks (pre-commit, commit-msg, pre-push). Less specific.
- **Parent process inspection**: Check if parent PID is git. Unreliable across platforms and shell wrappers.
- **CLI flag `--hook`**: Requires modifying the CLI interface. Works but adds unnecessary surface area.

**Implementation approach**:
- In the pre-commit hook bash script, export `DEV_STACK_HOOK_CONTEXT=pre-commit` before calling `dev-stack pipeline run`.
- In `PipelineRunner`, check `os.environ.get("DEV_STACK_HOOK_CONTEXT") == "pre-commit"` to determine auto-staging behavior.
- This is explicit, testable, and doesn't rely on git internals.

## R3: Comparing detect-secrets Baseline Findings (Ignoring Timestamps)

**Task**: Research how to compare `.secrets.baseline` findings while ignoring the `generated_at` timestamp.

### Decision: Load both old and new JSON, compare `results` dict only

**Rationale**:
- The `.secrets.baseline` JSON structure has a top-level `generated_at` field (ISO timestamp) and a `results` dict mapping file paths to lists of findings.
- The `generated_at` field changes on every `detect-secrets scan --baseline` invocation, even when no findings changed.
- Comparing the `results` section alone (after normalizing) gives a reliable determination of whether actual findings changed.
- `detect-secrets` does NOT provide a `--no-timestamp` or `--compare-only` flag.

**Alternatives considered**:
- **Shell-level diff ignoring `generated_at`**: `jq 'del(.generated_at)'` before comparison. Rejected: introduces `jq` dependency.
- **Run `detect-secrets scan` to stdout and compare**: Pipe to stdout instead of `--baseline`, compare findings. Rejected: `--baseline` flag also updates audit decisions; stdout mode doesn't merge with existing audits.
- **Restore original `generated_at` after scan**: Run scan (which overwrites file), then read the new file and replace `generated_at` with the original. Rejected: more complex than necessary and still writes to disk.

**Implementation approach**:
1. Before running `detect-secrets scan --baseline`, read and parse the existing `.secrets.baseline` JSON. Extract the `results` dict.
2. Run `detect-secrets scan --baseline` as normal (this overwrites the file with new timestamp).
3. Read and parse the updated `.secrets.baseline`. Extract the new `results` dict.
4. If `old_results == new_results`, restore the original file content (preserving the old timestamp).
5. If results differ, leave the new file in place (it will be auto-staged).

## R4: Detecting `-m` Flag in Commit-Message Stage

**Task**: Research how the commit-message stage can detect whether the user provided a message via `-m`.

### Decision: Check `.git/COMMIT_EDITMSG` content pattern and hook source argument

**Rationale**:
- Git's `commit-msg` hook receives the path to the commit message file as `$1`. The `pre-commit` hook does NOT receive this.
- However, the pipeline runs during `pre-commit`, not `commit-msg`. At pre-commit time, `.git/COMMIT_EDITMSG` may not exist yet (git writes it later), OR if `-m` was used, git may have already created it.
- The most reliable detection: git sets `GIT_AUTHOR_DATE` and passes commit info, but doesn't explicitly expose `-m` vs interactive mode to hooks.
- Pragmatic approach: Check if `.git/COMMIT_EDITMSG` exists AND contains content at the time the commit-message stage runs. If it does, the user likely provided `-m`. If not, the commit is interactive.
- Even more reliable: the pre-commit hook can pass the original `$@` arguments to `dev-stack pipeline run`, and the pipeline can check if any argument to `git commit` was `-m` or `--message`.

**Alternatives considered**:
- **Move commit-message generation to commit-msg hook**: The `commit-msg` hook has direct access to the message file. Rejected: would require architectural change to move one stage out of the pipeline.
- **Always generate, let git overwrite**: Generate the message, accept that `-m` overrides it. Just fix the status report. Rejected: wasteful to invoke the agent (180s timeout) when the result will be discarded.
- **Check `$GIT_PARAMS`**: No standard env var for this.

**Implementation approach**:
- In the pre-commit bash hook, pass git commit arguments to `dev-stack pipeline run`: `dev-stack pipeline run "$@"`.
- In `_execute_commit_stage`, check if `.git/COMMIT_EDITMSG` already exists with user content. If so, report "skip" with message: "User-supplied commit message detected (-m flag); skipping generated message."
- This avoids wasting agent invocation time on a message that will be overwritten.

## R5: CodeBoarding LLM API Key Detection

**Task**: Research which API keys CodeBoarding supports and how to pre-check them.

### Decision: Check 5 environment variables before invoking CodeBoarding

**Rationale**:
- CodeBoarding 0.9.x supports multiple LLM providers. The error message seen during testing lists: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`.
- Pre-checking these variables is faster and provides a better user experience than letting CodeBoarding fail with a raw error.
- The check is a simple `os.environ.get()` for each key — no external dependencies needed.

**Alternatives considered**:
- **Catch CodeBoarding's error and convert to skip**: Run CodeBoarding, catch the specific error message, convert to a skip. Rejected: still shows partial error output, and incurs subprocess startup cost.
- **Check only 2 keys (Anthropic, OpenAI)**: Simpler but would miss users with other providers. Rejected per spec clarification Q3.

**Implementation approach**:
- Define `LLM_API_KEY_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY")` in `stages.py`.
- In `_execute_visualize_stage`, after checking CLI availability, add: `if not any(os.environ.get(k) for k in LLM_API_KEY_VARS): return skip`.
- Include the variable names in the skip message for user guidance.

## R6: Pipeline Output Manifest Design

**Task**: Research the best approach for tracking which files each stage produces.

### Decision: Each stage executor returns output paths in StageResult

**Rationale**:
- The current `StageResult` dataclass has: `stage_name`, `status`, `failure_mode`, `duration_ms`, `output`, `skipped_reason`.
- Adding an `output_paths: list[Path]` field allows each stage to declare what files it created/modified.
- The runner can then collect paths from all "pass" or "skip" results and auto-stage them.
- This is more maintainable than a hardcoded central manifest because adding a new stage automatically supports auto-staging.

**Alternatives considered**:
- **Central hardcoded manifest in runner.py**: A dict mapping stage names to known output paths. Rejected: requires updating two places (stage + manifest) when adding stages.
- **Working-tree diff before/after**: Snapshot `git status` before pipeline, diff after. Rejected: too broad — would capture unrelated changes the user made.
- **Stage decorator**: `@outputs(".secrets.baseline")` decorator on executor functions. Rejected: over-engineered for the current number of stages.

**Implementation approach**:
- Add `output_paths: list[Path] = field(default_factory=list)` to `StageResult`.
- Each stage executor populates `output_paths` with the absolute paths of files it creates/modifies.
- In `PipelineRunner.run()`, after all stages complete, collect `output_paths` from results with status "pass" or "skip".
- Call `_auto_stage_outputs(paths)` which runs `git add` for each path that exists and is not in `.gitignore`.
