# Tasks: Version Control Best Practices Automation

**Input**: Design documents from `/specs/004-vcs-best-practices/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Each user story includes test tasks per the constitution's Quality Standards ("New code MUST include corresponding tests"). Test file paths align with plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/dev_stack/` source, `tests/` at repository root
- Paths follow existing dev-stack layout per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new packages and add dependencies required by all user stories.

- [X] T001 Create rules package with `__init__.py` exporting rule classes in `src/dev_stack/rules/__init__.py`
- [X] T002 [P] Create vcs package with `__init__.py` in `src/dev_stack/vcs/__init__.py`
- [X] T003 [P] Add `gitlint-core` to project dependencies in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Implement VcsConfig, HooksConfig, BranchConfig, SigningConfig dataclasses and `load_vcs_config()` loader reading `[tool.dev-stack.*]` from pyproject.toml in `src/dev_stack/vcs/__init__.py`
- [X] T005 [P] Implement HookManifest and HookEntry dataclasses with `to_dict()`/`from_dict()` JSON serialization and VcsHooksModule class shell (NAME, VERSION, DEPENDS_ON, MANAGED_FILES, MANAGED_HEADER) in `src/dev_stack/modules/vcs_hooks.py`
- [X] T006 [P] Create commit-msg thin Python hook wrapper template with shebang, managed header, and `run_commit_msg_hook()` import in `src/dev_stack/templates/hooks/commit-msg.py`
- [X] T007 [P] Create pre-push thin Python hook wrapper template with shebang, managed header, and `run_pre_push_hook()` import in `src/dev_stack/templates/hooks/pre-push.py`
- [X] T008 [P] Create pre-commit thin Python hook wrapper template running lint + typecheck pipeline stages (FR-016) in `src/dev_stack/templates/hooks/pre-commit.py`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 — Commit Message Linting on Every Commit (Priority: P1) MVP

**Goal**: Validate every commit message against conventional commit format and trailer rules via the commit-msg hook. Rejections produce clear, actionable errors.

**Independent Test**: Initialize a dev-stack project, attempt commits with valid and invalid messages, verify acceptance scenarios 1–6 from spec.md.

### Implementation for User Story 1

- [X] T009 [P] [US1] Implement ConventionalCommitRule (UC1) validating subject matches `type(scope): description` pattern with 11 valid types in `src/dev_stack/rules/conventional.py`
- [X] T010 [P] [US1] Implement TrailerPresenceRule (UC2) requiring all five trailers on agent commits and TrailerPathRule (UC3) validating Spec-Ref/Task-Ref path existence in `src/dev_stack/rules/trailers.py`
- [X] T011 [P] [US1] Implement PipelineFailureWarningRule (UC4) parsing Pipeline trailer and emitting non-blocking warnings for `=fail` entries in `src/dev_stack/rules/pipeline_warn.py`
- [X] T012 [US1] Implement `run_commit_msg_hook(msg_file_path: str) -> int` integrating all four rules via gitlint LintConfig with `extra_path` in `src/dev_stack/vcs/hooks_runner.py`

### Tests for User Story 1

- [X] T013 [P] [US1] Unit tests for ConventionalCommitRule: valid/invalid subjects, all 11 types, missing scope, oversized description in `tests/unit/test_rules_conventional.py`
- [X] T014 [P] [US1] Unit tests for TrailerPresenceRule and TrailerPathRule: agent vs manual commits, missing trailers, non-existent paths in `tests/unit/test_rules_trailers.py`

**Checkpoint**: Commit message validation works when `run_commit_msg_hook()` is called directly. Delivers value by catching malformed commits and missing trailers.

---

## Phase 4: User Story 2 — Git Hook Lifecycle Management (Priority: P1)

**Goal**: Install, track, update, and remove managed git hooks (`commit-msg`, `pre-push`, optionally `pre-commit`) via VcsHooksModule lifecycle and `dev-stack hooks status` CLI.

**Independent Test**: Run `dev-stack init`, inspect `.git/hooks/` for managed hook files, verify `dev-stack hooks status` output, run `dev-stack uninstall` to confirm cleanup.

### Implementation for User Story 2

- [X] T015 [US2] Implement VcsHooksModule.install() — copy hook templates to `.git/hooks/`, set `chmod 0o755`, detect and skip unmanaged existing hooks (FR-013), optionally install pre-commit hook when configured (FR-016), write `.dev-stack/hooks-manifest.json` in `src/dev_stack/modules/vcs_hooks.py`
- [X] T016 [US2] Implement VcsHooksModule.uninstall() — load manifest, verify checksums, delete only matching hooks, clear manifest in `src/dev_stack/modules/vcs_hooks.py`
- [X] T017 [US2] Implement VcsHooksModule.update() — compare current checksums against manifest, auto-update unmodified hooks with new templates (FR-014a), skip and warn on modified hooks in `src/dev_stack/modules/vcs_hooks.py`
- [X] T018 [US2] Implement VcsHooksModule.verify() — check hook file existence, validate checksums against manifest, report health; detect hook/manifest mismatch after rollback and recommend re-sync in `src/dev_stack/modules/vcs_hooks.py`
- [X] T019 [US2] Implement `run_pre_commit_hook() -> int` running lint + typecheck pipeline stages in `src/dev_stack/vcs/hooks_runner.py`
- [X] T020 [US2] Implement `dev-stack hooks status` CLI command with `--json` output per cli-contract.md schema in `src/dev_stack/cli/hooks_cmd.py`
- [X] T021 [US2] Register VcsHooksModule in module registry in `src/dev_stack/modules/__init__.py` and import hooks_cmd in `src/dev_stack/cli/main.py`

### Tests for User Story 2

- [X] T022 [P] [US2] Unit tests for VcsHooksModule install/uninstall/update/verify lifecycle in `tests/unit/test_vcs_hooks_module.py`
- [X] T023 [P] [US2] Integration tests for hooks lifecycle: init → status → modify → update → uninstall in `tests/integration/test_hooks_lifecycle.py`
- [X] T024 [P] [US2] Contract tests for `hooks status` JSON schema compliance in `tests/contract/test_cli_hooks.py`

**Checkpoint**: `dev-stack init` installs managed hooks (including pre-commit when configured), `dev-stack hooks status` reports their state, and `dev-stack uninstall` cleanly removes them. US1 commit linting is now enforced automatically on every commit.

---

## Phase 5: User Story 3 — Branch Naming Enforcement (Priority: P2)

**Goal**: Validate branch names against a configurable regex pattern at push time via the pre-push hook. Never block local branch creation.

**Independent Test**: Create branches with valid (`feat/my-feature`) and invalid (`my-random-branch`) names, attempt `git push`, verify enforcement per acceptance scenarios 1–5 from spec.md.

### Implementation for User Story 3

- [X] T025 [P] [US3] Implement `validate_branch_name()` with configurable pattern regex, exempt branch list, and spec-kit branch mismatch warning in `src/dev_stack/vcs/branch.py`
- [X] T026 [US3] Implement `run_pre_push_hook(stdin: IO[str]) -> int` parsing push info from stdin and calling branch validation in `src/dev_stack/vcs/hooks_runner.py`

### Tests for User Story 3

- [X] T027 [P] [US3] Unit tests for branch name validation: default pattern, custom pattern, exempt list, spec-kit mismatch warning in `tests/unit/test_branch.py`
- [X] T028 [P] [US3] Integration tests for pre-push hook: valid/invalid branch push, exempt branches in `tests/integration/test_pre_push.py`

**Checkpoint**: Branch naming enforcement works at push time. Valid branches push freely, invalid ones are blocked with clear error messages.

---

## Phase 6: User Story 4 — Constitutional Practices for Agents (Priority: P2)

**Goal**: Generate constitution template and instructions file during `dev-stack init`, detect agent-specific files, and inject managed instruction sections.

**Independent Test**: Run `dev-stack init`, verify `constitution-template.md` contains Atomic Commits and TDD subsections, verify `.dev-stack/instructions.md` exists, verify agent file injection uses managed markers.

### Implementation for User Story 4

- [X] T029 [P] [US4] Create constitution template content with "Dev-Stack Baseline Practices" header, "Atomic Commits" subsection (FR-020), "Test-Driven Development" subsection (FR-021), and "User-Defined Requirements" section in `src/dev_stack/templates/constitution-template.md`
- [X] T030 [P] [US4] Create agent instructions template with atomic commit and TDD clauses in `src/dev_stack/templates/instructions.md`
- [X] T031 [US4] Extend VcsHooksModule.install() to generate `constitution-template.md` at repo root, create `.dev-stack/instructions.md`, detect agent files (`.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`), and inject managed sections using `write_managed_section()` with `DEV-STACK:INSTRUCTIONS` section ID in `src/dev_stack/modules/vcs_hooks.py`

**Checkpoint**: `dev-stack init` produces constitutional templates and instructions. Agent files receive managed instruction sections that are idempotent on re-init.

---

## Phase 7: User Story 5 — PR Auto-Description Generation (Priority: P3)

**Goal**: Collect branch commits, aggregate trailers, and render a structured Markdown PR description. Optionally create the PR via `gh` or `glab`.

**Independent Test**: Create a branch with several commits (some with trailers), run `dev-stack pr --dry-run`, verify rendered Markdown includes summary, spec refs, task refs, AI provenance, pipeline status, and commit list.

### Implementation for User Story 5

- [X] T032 [P] [US5] Implement CommitSummary dataclass and `parse_commits(base: str, head: str) -> list[CommitSummary]` git log parsing utility in `src/dev_stack/vcs/commit_parser.py`
- [X] T033 [P] [US5] Create PR description Markdown template with Summary, Spec References, Task References, AI Provenance, Pipeline Status, and Commits sections in `src/dev_stack/templates/pr-template.md`
- [X] T034 [US5] Implement PRDescription dataclass, trailer aggregation, and Markdown rendering from template in `src/dev_stack/vcs/pr.py`
- [X] T035 [US5] Implement `dev-stack pr` CLI command with `--dry-run`, `--base`, `--json` flags, `gh`/`glab` detection, and register in `src/dev_stack/cli/pr_cmd.py` and `src/dev_stack/cli/main.py`

### Tests for User Story 5

- [X] T036 [P] [US5] Unit tests for PR description rendering: trailer aggregation, template output, edge cases (no commits, no trailers) in `tests/unit/test_pr.py`
- [X] T037 [P] [US5] Contract tests for `pr` JSON schema compliance in `tests/contract/test_cli_pr.py`

**Checkpoint**: `dev-stack pr --dry-run` renders complete PR descriptions from branch commit history. PR creation works when `gh` or `glab` is available.

---

## Phase 8: User Story 6 — Changelog Generation (Priority: P3)

**Goal**: Generate or update `CHANGELOG.md` grouped by conventional commit type, with AI-authored and human-edited annotations, using git-cliff.

**Independent Test**: Make a series of conventional commits, run `dev-stack changelog --unreleased`, verify output groups changes by type with correct annotations.

### Implementation for User Story 6

- [X] T038 [P] [US6] Create cliff.toml template with conventional commit parsers, commit type-to-group mapping, and Tera template rendering AI/human-edited markers from commit footers in `src/dev_stack/templates/cliff.toml`
- [X] T039 [US6] Implement changelog generation wrapper invoking `git-cliff` subprocess with `--unreleased`/full modes and post-processing trailer annotations in `src/dev_stack/vcs/changelog.py`
- [X] T040 [US6] Implement `dev-stack changelog` CLI command with `--unreleased`, `--full`, `--output`, `--json` flags, git-cliff availability check, and register in `src/dev_stack/cli/changelog_cmd.py` and `src/dev_stack/cli/main.py`
- [X] T041 [US6] Add cliff.toml generation from template to VcsHooksModule.install() in `src/dev_stack/modules/vcs_hooks.py`

### Tests for User Story 6

- [X] T042 [P] [US6] Unit tests for changelog generation: group mapping, AI/human-edited markers, missing git-cliff error handling in `tests/unit/test_changelog.py`
- [X] T043 [P] [US6] Contract tests for `changelog` JSON schema compliance in `tests/contract/test_cli_changelog.py`

**Checkpoint**: `dev-stack changelog` produces properly grouped changelogs with AI provenance markers. `cliff.toml` is generated during `dev-stack init`.

---

## Phase 9: User Story 7 — Semantic Release Versioning (Priority: P3)

**Goal**: Infer next semantic version from conventional commit types, bump `pyproject.toml`, generate changelog entry, and create annotated git tag. Refuse release on hard pipeline failures.

**Independent Test**: Create commits of various types (`feat`, `fix`, `BREAKING CHANGE`), run `dev-stack release --dry-run`, verify correct semver bump and listed actions.

### Implementation for User Story 7

- [X] T044 [US7] Implement ReleaseContext dataclass, version inference from commit types, release gate check (reject on hard Pipeline failures), `pyproject.toml` version bumping via tomli/tomli_w, annotated tag creation, and PSR delegation with built-in fallback in `src/dev_stack/vcs/release.py`
- [X] T045 [US7] Implement `dev-stack release` CLI command with `--dry-run`, `--bump {major,minor,patch}`, `--no-tag`, `--json` flags, and register in `src/dev_stack/cli/release_cmd.py` and `src/dev_stack/cli/main.py`

### Tests for User Story 7

- [X] T046 [P] [US7] Unit tests for release: version inference (feat→minor, fix→patch, breaking→major), gate check (hard failures block), PSR fallback in `tests/unit/test_release.py`
- [X] T047 [P] [US7] Contract tests for `release` JSON schema compliance in `tests/contract/test_cli_release.py`

**Checkpoint**: `dev-stack release` correctly infers version bumps, enforces the release gate, and produces tagged releases. Built-in fallback works when python-semantic-release is not installed.

---

## Phase 10: User Story 8 — Signed Commit Enforcement (Priority: P4)

**Goal**: Opt-in SSH commit signing configured during `dev-stack init`. Pre-push hook warns or blocks if agent-generated commits are unsigned.

**Independent Test**: Enable signing in `pyproject.toml`, run `dev-stack init`, verify git config values, attempt to push unsigned agent-generated commits.

### Implementation for User Story 8

- [X] T048 [US8] Implement SSH key auto-detection (`find_ssh_public_key()`), git version check (`supports_ssh_signing()`), `configure_ssh_signing()` setting local git config, and `get_unsigned_agent_commits()` in `src/dev_stack/vcs/signing.py`
- [X] T049 [US8] Add signing configuration call to VcsHooksModule.install() — check git version (FR-040a), detect SSH key (FR-041), set `commit.gpgsign`/`gpg.format`/`user.signingkey` via local git config in `src/dev_stack/modules/vcs_hooks.py`
- [X] T050 [US8] Extend `run_pre_push_hook()` to check for unsigned agent commits in push range and apply warn/block enforcement per SigningConfig in `src/dev_stack/vcs/hooks_runner.py`

### Tests for User Story 8

- [X] T051 [P] [US8] Unit tests for signing: key detection, git version check, unsigned agent commit detection, enforcement modes in `tests/unit/test_signing.py`

**Checkpoint**: SSH signing is configured during init when enabled. Pre-push hook enforces signing policy on agent-generated commits only.

---

## Phase 11: User Story 9 — Scope Advisory Check in Pipeline (Priority: P4)

**Goal**: Non-blocking heuristic check detecting when staged changes span multiple unrelated concerns, surfacing `scope-check=warn` in the Pipeline trailer.

**Independent Test**: Stage files across 3+ source subpackages, run commit-message pipeline stage, verify `scope-check=warn` appears in Pipeline trailer.

### Implementation for User Story 9

- [X] T052 [P] [US9] Implement `check_scope(staged_files: list[str]) -> ScopeAdvisory` with three independent trigger rules: 3+ repo-root dirs, 3+ source subpackages, and specs+src overlap in `src/dev_stack/vcs/scope.py`
- [X] T053 [US9] Integrate scope advisory into `_execute_commit_stage()` — call `check_scope()` against staged files and append `scope-check=warn` to pipeline results when triggered in `src/dev_stack/pipeline/stages.py`

### Tests for User Story 9

- [X] T054 [P] [US9] Unit tests for scope advisory: all three trigger rules, non-triggering cases, never-blocks assertion in `tests/unit/test_scope.py`

**Checkpoint**: Scope advisory fires correctly for multi-concern changes. Never blocks commits — informational only.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation.

- [X] T055 [P] Add signing status display (enabled/enforcement/key/git version) to `dev-stack hooks status` output in `src/dev_stack/cli/hooks_cmd.py`
- [X] T056 Validate all CLI commands produce correct `--json` output matching schemas in `specs/004-vcs-best-practices/contracts/cli-contract.md`
- [X] T057 Run quickstart.md end-to-end validation against implemented commands in `specs/004-vcs-best-practices/quickstart.md`
- [X] T058 Performance validation: verify hook ops < 2s (SC-006), constitution gen < 1s (SC-008), scope check < 500ms (SC-010) in a benchmark test

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — requires `rules/` package, gitlint dep
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — requires VcsHooksModule shell, hook templates
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — requires VcsConfig, pre-push template
- **US4 (Phase 6)**: Depends on Foundational (Phase 2) — extends VcsHooksModule.install()
- **US5 (Phase 7)**: Depends on Foundational (Phase 2) — no cross-story deps (CommitSummary is self-contained)
- **US6 (Phase 8)**: Depends on Foundational (Phase 2) — extends VcsHooksModule.install()
- **US7 (Phase 9)**: Depends on Phase 7 (reuses CommitSummary from `commit_parser.py`)
- **US8 (Phase 10)**: Depends on Phase 5 (extends `run_pre_push_hook()`)
- **US9 (Phase 11)**: Depends on Foundational (Phase 2) — modifies `stages.py` independently
- **Polish (Phase 12)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent — no dependencies on other stories
- **US2 (P1)**: Independent — no dependencies on other stories (US1 rules are imported dynamically by hook)
- **US3 (P2)**: Independent — creates `run_pre_push_hook()` in separate function
- **US4 (P2)**: Independent — extends install() with template generation
- **US5 (P3)**: Independent — introduces CommitSummary and commit parsing
- **US6 (P3)**: Independent — wraps git-cliff
- **US7 (P3)**: Soft dependency on US5 (reuses `commit_parser.py`), but can create its own parsing if US5 not done
- **US8 (P4)**: Extends `run_pre_push_hook()` from US3; if US3 not done, creates the function instead
- **US9 (P4)**: Independent — modifies `stages.py` directly

### Within Each User Story

- Models/dataclasses → services/utilities → CLI commands → integration
- Core implementation before cross-module integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 — all different files
- **Phase 2**: T004, T005, T006, T007, T008 — all different files
- **Phase 3 (US1)**: T009, T010, T011 — three different rule files; T012 depends on all three; T013, T014 parallel test files
- **Phase 4 (US2)**: T015→T016→T017→T018 sequential (same file); T019 parallel (hooks_runner.py); T020 parallel after T018; T021 last; T022, T023, T024 parallel test files
- **Phase 5 (US3)**: T025 parallel (branch.py); T026 depends on T025; T027, T028 parallel test files
- **Phase 6 (US4)**: T029, T030 parallel (template files); T031 depends on both
- **Phase 7 (US5)**: T032, T033 parallel; T034 depends on T032; T035 depends on T034; T036, T037 parallel test files
- **Phase 8 (US6)**: T038 parallel (template); T039 depends; T040 depends on T039; T041 independent; T042, T043 parallel test files
- **After Foundational**: US1, US2, US3, US4, US5, US6 can ALL start in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all rule implementations in parallel (different files):
Task T009: "Implement ConventionalCommitRule in src/dev_stack/rules/conventional.py"
Task T010: "Implement TrailerPresenceRule and TrailerPathRule in src/dev_stack/rules/trailers.py"
Task T011: "Implement PipelineFailureWarningRule in src/dev_stack/rules/pipeline_warn.py"

# Then sequential (depends on all three rules):
Task T012: "Implement run_commit_msg_hook() in src/dev_stack/vcs/hooks_runner.py"

# Then parallel tests:
Task T013: "Unit tests for ConventionalCommitRule in tests/unit/test_rules_conventional.py"
Task T014: "Unit tests for TrailerPresenceRule in tests/unit/test_rules_trailers.py"
```

## Parallel Example: Cross-Story (after Foundational)

```bash
# All P1+P2 stories can start simultaneously:
Developer A: US1 (T009-T014) — Commit linting rules + tests
Developer B: US2 (T015-T024) — Hook lifecycle module + CLI + tests
Developer C: US3 (T025-T028) — Branch naming + tests
Developer D: US4 (T029-T031) — Constitutional practices
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (packages + dependency)
2. Complete Phase 2: Foundational (config, manifest, templates)
3. Complete Phase 3: US1 — Commit message linting rules + hook runner + tests
4. Complete Phase 4: US2 — Hook lifecycle management + `hooks status` CLI + tests
5. **STOP and VALIDATE**: Commits are now validated, hooks are managed
6. Deploy/demo: Core enforcement loop is functional

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 + US2 → Commit enforcement active (MVP!)
3. US3 + US4 → Branch naming + agent practices (P2 increment)
4. US5 + US6 + US7 → PR, changelog, release automation (P3 increment)
5. US8 + US9 → Signing + scope advisory (P4 increment)
6. Each increment adds value without breaking previous stories

### Single Developer Strategy

1. Complete Setup + Foundational (T001–T008)
2. US1 → US2 → US3 → US4 → US5 → US6 → US7 → US8 → US9
3. Polish (T055–T058)
4. Each story is independently testable at its checkpoint

---

## Notes

- [P] tasks = different files, no dependencies on concurrent tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Test tasks are included per constitution Quality Standards ("New code MUST include corresponding tests")
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- FR references in descriptions map to functional requirements in spec.md
