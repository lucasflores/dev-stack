# Tasks: Pipeline Commit Fixes

**Input**: Design documents from `/specs/011-pipeline-commit-fixes/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included in Polish phase — the plan explicitly lists test files as NEW/MODIFY.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup

**Purpose**: Create the new standalone module that multiple stories depend on

- [X] T001 Create response_parser.py with ExtractionMethod enum, ParsedCommitMessage dataclass, and extract_commit_message() function per contracts/response-parser.md in src/dev_stack/pipeline/response_parser.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure changes that MUST complete before any user story can be implemented

**⚠️ CRITICAL**: Stage filtering and debug logging are prerequisites for all story-level work

- [X] T002 Add _configure_debug_logging() function that activates file-based logging when DEV_STACK_DEBUG=1 per contracts/debug-logging.md in src/dev_stack/pipeline/runner.py
- [X] T003 Add HOOK_STAGE_MAP constant and hook-context-aware stage filtering to PipelineRunner.run() so pre-commit runs stages 1-2 and prepare-commit-msg runs stages 3-9 per contracts/hook-context.md in src/dev_stack/pipeline/runner.py

**Checkpoint**: Foundation ready — response parser exists, stage filtering works, debug logging available

---

## Phase 3: User Story 1 — Commit message is clean and well-structured (Priority: P1) 🎯 MVP

**Goal**: Agent responses are parsed to extract only the clean conventional-commit text, stripping thinking traces, tool-use output, and code fences

**Independent Test**: Invoke extract_commit_message() with known raw agent output strings and verify only the final commit message is returned — no code fences, no thinking traces

### Implementation for User Story 1

- [X] T004 [P] [US1] Integrate extract_commit_message() into _execute_commit_stage, replacing direct response.content.strip() pass-through to upsert_trailers() with parsed output and failure handling in src/dev_stack/pipeline/stages.py
- [X] T005 [P] [US1] Add debug logging for response parsing events (extraction method, source_hash, success/failure, extracted subject length) in src/dev_stack/pipeline/response_parser.py

**Checkpoint**: Response parser extracts clean messages; raw agent noise no longer reaches commit messages

---

## Phase 4: User Story 2 — Generated commit message is actually recorded by git (Priority: P1)

**Goal**: Commit message generation moves to the prepare-commit-msg hook, which receives the message file path from git. Generated messages are written where git reads them.

**Independent Test**: Run `git commit` (no -m flag) in a test repo with hooks installed; inspect `git log -1 --format=%B` to confirm the pipeline-generated message was recorded

### Implementation for User Story 2

- [X] T006 [P] [US2] Create prepare-commit-msg shell wrapper template that passes $1 (message file), $2 (source), $3 (SHA) to dev-stack hooks CLI in src/dev_stack/templates/hooks/prepare-commit-msg
- [X] T007 [P] [US2] Create prepare-commit-msg.py Python entry point template with run_prepare_commit_msg_hook() call signature in src/dev_stack/templates/hooks/prepare-commit-msg.py
- [X] T008 [US2] Implement run_prepare_commit_msg_hook(message_file, source, commit_sha) with source-arg early exit for message/commit/merge/squash, env setup, pipeline invocation for stages 3-9, message file write (with try/except for PermissionError/OSError), and differential exit codes: stages 3-5 failure → exit 1, stage 9 failure → exit 0 (fallback to editor per FR-009/SC-007) per contracts/hook-context.md in src/dev_stack/vcs/hooks_runner.py
- [X] T009 [US2] Fix pre-commit shell wrapper template to invoke `dev-stack hooks run pre-commit` instead of `dev-stack pipeline run` so only stages 1-2 execute in src/dev_stack/templates/hooks/pre-commit
- [X] T010 [US2] Register prepare-commit-msg in hook installation/init logic so `dev-stack init` installs the new hook template alongside existing hooks in src/dev_stack/vcs/hooks_runner.py

**Checkpoint**: git commit records pipeline-generated messages; -m flag preserves user messages; prepare-commit-msg hook installed by init

---

## Phase 5: User Story 3 — Stale COMMIT_EDITMSG does not suppress message generation (Priority: P2)

**Goal**: The old _user_message_provided() function (which reads stale COMMIT_EDITMSG) is removed. Detection now uses the prepare-commit-msg hook's source argument, which is authoritative and per-invocation.

**Independent Test**: Run `git commit -m "first"`, then `git commit` (no -m) with new staged changes — pipeline correctly generates a message for the second commit

### Implementation for User Story 3

- [X] T011 [US3] Remove _user_message_provided() function and all call sites that reference COMMIT_EDITMSG-based message detection from src/dev_stack/pipeline/stages.py
- [X] T012 [US3] Add debug logging for hook context source-arg decisions (generate vs skip with reason) in run_prepare_commit_msg_hook in src/dev_stack/vcs/hooks_runner.py

**Checkpoint**: No COMMIT_EDITMSG reads for message detection; source-arg gating is the sole mechanism; stale state cannot cause false skips

---

## Phase 6: User Story 4 — Pipeline stages do not modify staged content (Priority: P2)

**Goal**: Agent invocations during hooks run in sandbox mode (no filesystem writes). Doc suggestions are saved as advisory output to .dev-stack/pending-docs.md instead of applied directly. Staged diff integrity is verified.

**Independent Test**: Record `git diff --cached` before pipeline, run full pipeline, compare `git diff --cached` after — byte-identical

### Implementation for User Story 4

- [X] T013 [US4] Add sandbox: bool = False parameter to AgentBridge.invoke() and pass it through to _build_command() in src/dev_stack/pipeline/agent_bridge.py
- [X] T014 [US4] Update _build_command for Copilot to use --deny-tool='write' and selective --allow-tool flags when sandbox=True, removing --allow-all and COPILOT_ALLOW_ALL per contracts/agent-sandbox.md in src/dev_stack/pipeline/agent_bridge.py
- [X] T015 [US4] Update _build_command for Claude and Cursor to add --disallowedTools Edit,Write,Bash when sandbox=True per contracts/agent-sandbox.md in src/dev_stack/pipeline/agent_bridge.py
- [X] T016 [P] [US4] Implement StagedSnapshot class with capture() classmethod using git diff --cached hashing and diff_hash comparison per data-model.md in src/dev_stack/pipeline/stages.py
- [X] T017 [US4] Add staged snapshot capture and comparison around agent invocations when DEV_STACK_HOOK_CONTEXT is set, raising StagedContentViolation on mismatch in src/dev_stack/pipeline/stages.py
- [X] T018 [US4] Convert _execute_docs_narrative_stage to advisory mode in hook context — implement _append_advisory_suggestion() and write to .dev-stack/pending-docs.md instead of direct file writes per contracts/advisory-docs.md in src/dev_stack/pipeline/stages.py

**Checkpoint**: Agents sandboxed during hooks; staged diff integrity verified; doc suggestions saved as advisory output

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tests, validation, and cleanup across all stories

- [X] T019 [P] Add unit tests for extract_commit_message() covering code-fence extraction, plain-text fallback, empty input rejection, multi-fence last-block selection, and tool-artifact rejection in tests/unit/test_response_parser.py
- [X] T020 [P] Update or replace test_user_message.py for source-arg-based detection replacing COMMIT_EDITMSG checks in tests/unit/test_user_message.py
- [X] T021 [P] Add prepare-commit-msg lifecycle tests verifying hook invocation, source-arg gating, message file write, and commit-message end-to-end integration in tests/integration/test_hooks_lifecycle.py (also covers plan.md's test_commit_message.py scope)
- [X] T022 [P] Verify hook installation includes prepare-commit-msg template in tests/contract/test_cli_hooks.py
- [X] T023 Run quickstart.md validation scenarios end-to-end (response parser, hook context, debug logging, advisory docs)
- [X] T024 Run full test suite with ruff lint and pytest to verify no regressions across existing tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (response_parser exists for later integration)
- **US1 (Phase 3)**: Depends on Phase 1 (response_parser) and Phase 2 (debug logging)
- **US2 (Phase 4)**: Depends on Phase 2 (stage filtering in runner.py)
- **US3 (Phase 5)**: Depends on Phase 4 (run_prepare_commit_msg_hook exists with source-arg gating)
- **US4 (Phase 6)**: Depends on Phase 2 (hook context env var mechanism)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent — only needs response_parser from Setup
- **US2 (P1)**: Independent — needs stage filtering from Foundational
- **US3 (P2)**: Depends on US2 — source-arg mechanism must exist before old detection is removed
- **US4 (P2)**: Independent — only needs hook context env var from Foundational
- **US1 + US2 can proceed in parallel** after Foundational completes
- **US3 + US4 can proceed in parallel** (US3 after US2, US4 after Foundational)

### Within Each User Story

- Core logic before integration/wiring
- Integration before cleanup
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 3 (US1)**: T004 (stages.py) ∥ T005 (response_parser.py) — different files
**Phase 4 (US2)**: T006 (prepare-commit-msg) ∥ T007 (prepare-commit-msg.py) — different files
**Phase 6 (US4)**: T013–T015 (agent_bridge.py) ∥ T016 (stages.py) — different files
**Phase 7**: T019 ∥ T020 ∥ T021 ∥ T022 — all different test files

---

## Parallel Example: User Story 1

```
# Launch both US1 tasks together (different files):
Task T004: "Integrate extract_commit_message() into _execute_commit_stage in stages.py"
Task T005: "Add debug logging for parse events in response_parser.py"
```

## Parallel Example: User Story 4

```
# Launch agent_bridge changes and StagedSnapshot in parallel (different files):
Task T013: "Add sandbox param to AgentBridge.invoke() in agent_bridge.py"
Task T016: "Implement StagedSnapshot class in stages.py"

# After both complete, wire them together:
Task T017: "Add snapshot comparison around agent invocations in stages.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T003)
3. Complete Phase 3: User Story 1 (T004–T005)
4. **STOP and VALIDATE**: Test response parser with known agent outputs
5. Commit messages are now clean — immediate value delivered

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Clean messages (MVP!)
3. Add US2 → Git records messages correctly
4. Add US3 → Stale detection eliminated (depends on US2)
5. Add US4 → Staged content protected
6. Polish → Tests, validation, regression check
7. Each story adds value without breaking previous stories

### Single-Developer Execution Order

1. T001 → T002 → T003 (Setup + Foundational)
2. T004 + T005 in parallel (US1)
3. T006 + T007 in parallel, then T008 → T009 → T010 (US2)
4. T011 → T012 (US3)
5. T013 + T016 in parallel, then T014 → T015 → T017 → T018 (US4)
6. T019 + T020 + T021 + T022 in parallel, then T023 → T024 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete same-phase tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable at its checkpoint
- Commit after each task or logical group
- US3 is intentionally small — the architectural fix (prepare-commit-msg hook) is in US2; US3 is cleanup of the old mechanism
