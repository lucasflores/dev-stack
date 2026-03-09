# Tasks: README Comprehensive Update

**Input**: Design documents from `/specs/005-readme-update/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/readme-section-contract.md, quickstart.md

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story. Since this is a documentation-only feature (single `README.md` file), parallelism within a phase is limited. The [P] marker is used only where tasks genuinely touch independent content within the same file without merge conflicts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent content, no overlap)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All tasks edit the same file: `README.md` at repository root

## Path Conventions

- **Deliverable**: `README.md` (repository root)
- **Reference docs**: `specs/005-readme-update/` (plan, research, data-model, contracts, quickstart)
- **Source of truth** for content: `src/dev_stack/` (modules, CLI, pipeline, vcs, rules, visualization)

---

## Phase 1: Setup

**Purpose**: Prepare for the rewrite — backup current README and create clean skeleton

- [X] T001 Create backup of current README at README.md.bak and replace README.md with a clean skeleton containing the `<h1>` title, tagline blockquote, and all 15 `<h2>` headings (per contracts/readme-section-contract.md Section 2 TOC) with empty placeholder bodies in README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Write the overarching introductory content that frames all user stories. These sections set context for everything below and MUST be complete before story-specific sections make sense.

**⚠️ CRITICAL**: All user story phases depend on these sections being written first.

- [X] T002 Write the Table of Contents with 15 anchor links matching the `<h2>` headings exactly per contracts/readme-section-contract.md Section 2 in README.md
- [X] T003 Write Section "What Is Dev-Stack?" (§3) — prose paragraph + bullet list mentioning all 9 modules (per data-model.md Module Catalog), 8-stage pipeline, CodeBoarding visualization, VCS practices, and UV Project scaffolding. Must NOT mention D2 or six-stage. Covers FR-001, FR-002 in README.md

**Checkpoint**: Skeleton + intro complete — user story implementation can now begin

---

## Phase 3: User Story 1 — New User Reads README and Successfully Initializes Dev-Stack (Priority: P1) 🎯 MVP

**Goal**: A new developer can follow the README top-to-bottom to install prerequisites, set up the CLI, bootstrap a project, and verify it works — without consulting any spec document.

**Independent Test**: Execute every code block from Prerequisites through Validation Checklist on a clean machine. All commands succeed. Compare CLI table against `dev-stack --help` — zero mismatches (SC-001, SC-005).

### Implementation for User Story 1

- [X] T004 [US1] Write Section "Prerequisites" (§5) — single consolidated table with columns Tool | Purpose | Required? containing 10 rows (4 required: Python 3.11+, uv, git 2.30+, coding agent CLI; 6 optional: CodeBoarding, mypy, sphinx, git-cliff, python-semantic-release, gh/glab) with graceful-degradation notes. Remove d2 entirely. Covers FR-009 in README.md
- [X] T005 [US1] Write Section "Quickstart" (§6) — code blocks for `git clone`, `uv sync`, editable install, and `dev-stack --help` smoke test. Remove any d2 from brew install. Must work as a standalone getting-started flow. Validates SC-005 in README.md
- [X] T006 [US1] Write Section "Install Dev-Stack In Your Repo" (§7) — 3 numbered subsections (Install CLI, Bootstrap via `dev-stack init`, Review generated assets). Assets table must contain all 15 rows from data-model.md Generated Assets entity including new entries: constitution-template.md, .dev-stack/instructions.md, cliff.toml, .git/hooks/commit-msg, .git/hooks/pre-push, docs/conf.py, docs/index.rst. Verify existing asset rows (e.g., `.pre-commit-config.yaml`, agent config path) are still accurate. Document greenfield mode (uv init --package). Covers FR-010, FR-015 in README.md
- [X] T007 [US1] Write Section "CLI Essentials" (§8) — single command table with 12 rows: init, update, rollback, `mcp install|verify`, `pipeline run`, visualize, status, changelog, `hooks status`, pr, release, version. Include key flags for each command (especially --depth-level, --incremental, --no-readme, --timeout for visualize; --json and --dry-run as footer note). VCS commands (changelog, hooks status, pr, release) must have accurate descriptions matching data-model.md CLI Command entity. Covers FR-003, FR-006, FR-007 in README.md
- [X] T008 [US1] Write Section "Validation Checklist" (§12) — 6-8 numbered verification items with code examples (check CLI, check modules, check pipeline, check hooks, check visualization, check config). Reference quickstart.md for detailed verification. Supports SC-005, FR-017 (dual-audience flow) in README.md

**Checkpoint**: A new user can follow Prerequisites → Quickstart → Install → CLI Essentials → Validation end-to-end

---

## Phase 4: User Story 2 — Existing User Discovers New Capabilities (Priority: P1)

**Goal**: A returning user scans the README and discovers all new features from specs 002–004: new modules (UV Project, Sphinx Docs, VCS Hooks), expanded 8-stage pipeline, CodeBoarding visualization, and new CLI commands — without encountering any stale D2 references.

**Independent Test**: Compare Module Catalog against `src/dev_stack/modules/*.py` — zero omissions (SC-002). Compare Pipeline table against `build_pipeline_stages()` — all 8 stages correct (SC-004). Grep for D2 — zero matches (SC-003).

### Implementation for User Story 2

- [X] T009 [US2] Write Section "Key Capabilities" (§4) — emoji bullet list (5–7 items) covering: module-driven scaffolding, 8-stage pipeline, CodeBoarding visualization, VCS enforcement (commit linting, branch naming, signing), Python project scaffolding (UV), constitutional agent instructions. Covers FR-003, FR-007, FR-015, FR-016 in README.md
- [X] T010 [US2] Write Section "Module Catalog" (§9) — table with columns Module | Managed Assets | Highlights containing all 9 modules from data-model.md. VCS Hooks row must describe commit linting, branch naming, signing, and constitutional instructions. Sphinx Docs row must mention docs/conf.py, docs/index.rst, docs/Makefile and docs/_build/ gitignored. Visualization row must reference CodeBoarding (not D2). Covers FR-001, FR-007, FR-014, FR-016 in README.md
- [X] T011 [US2] Write Section "Automation Pipeline" (§10) — table with columns # | Stage | Mode | Description containing all 8 stages in exact order from data-model.md Pipeline Stage entity. Stages 1-5 hard gate, stages 6-8 soft gate. Footer notes explaining hard (halt on fail) vs soft (warn, allow with --force). Covers FR-002 in README.md
- [X] T012 [US2] Write Section "Visualization Workflow" (§11) — 3 numbered steps: (1) Invoke CodeBoarding CLI via codeboarding_runner.py, (2) Parse .codeboarding/analysis.json for Mermaid diagrams via output_parser.py, (3) Inject Mermaid blocks into README with managed markers via readme_injector.py. Document --depth-level (default 2), per-folder sub-diagrams, --no-readme, --incremental flags. Must NOT mention D2, d2_gen, schema_gen, noodles, SVG/PNG rendering. Covers FR-004, FR-005, FR-006 in README.md

**Checkpoint**: Returning users can discover all new modules, pipeline stages, and visualization workflow

---

## Phase 5: User Story 3 — Developer Understands VCS Best Practices Workflow (Priority: P2)

**Goal**: A developer reads the README and understands how to configure and use all VCS automation: commit linting, branch naming, signing, PR generation, changelog, release, and scope advisory — all distributed into existing sections per clarification Q2.

**Independent Test**: A developer reads only VCS-related content in the README and successfully configures commit linting, pushes a compliant branch, generates a PR description, creates a changelog, and performs a release.

### Implementation for User Story 3

- [X] T013 [US3] Write Section "Configuration" (§13) — code block showing pyproject.toml `[tool.dev-stack.*]` sections with examples for: branch naming pattern (`[tool.dev-stack.branch]`), hook selection (`[tool.dev-stack.hooks]`), signing settings (`[tool.dev-stack.signing]`), and any other VCS-related knobs. Explain how settings affect hook and pipeline behavior. Covers FR-008 in README.md
- [X] T014 [US3] Review and enrich VCS content depth across previously written sections per FR-007. Definition of done: (1) CLI Essentials `changelog` row includes `--unreleased|--full` flags, (2) CLI Essentials `hooks status` row mentions checksum/modification status, (3) CLI Essentials `pr` row mentions `--dry-run` and `gh`/`glab` fallback to stdout, (4) CLI Essentials `release` row mentions `--bump LEVEL` and `--no-tag`, (5) Module Catalog VCS Hooks row explains commit-msg validates conventional format + trailers AND pre-push enforces branch naming, (6) Pipeline `commit-message` stage description mentions structured narrative + trailers, (7) Configuration section references scope advisory behavior in README.md

**Checkpoint**: VCS practices are fully documented and discoverable across existing sections

---

## Phase 6: User Story 4 — README Accurately Reflects Repository Structure (Priority: P2)

**Goal**: The repository layout, architecture snapshot, development workflow, and spec references are accurate and up-to-date, enabling contributors to navigate the codebase using only the README.

**Independent Test**: Compare Repository Layout tree against actual file system — zero missing significant directories (SC-006). Confirm all 4 spec directories referenced (SC-007).

### Implementation for User Story 4

- [X] T015 [P] [US4] Write Section "Repository Layout" (§14) — ASCII tree showing src/dev_stack/ with all packages: cli/, modules/, pipeline/, brownfield/, vcs/, rules/, visualization/, templates/. Show specs/001–004/ directories. Show tests/ structure. Must include vcs/ and rules/ (new packages). Covers FR-011 in README.md
- [X] T016 [P] [US4] Write Section "Architecture Snapshot" (§15) — bullet list describing each source package: vcs/ (commit parsing, branch validation, PR/changelog/release, signing, scope), rules/ (gitlint custom rules for conventional commits and trailers), visualization/ (CodeBoarding runner, output parser, README injector, incremental diffing), pipeline/ (8-stage orchestrator), modules/ (9 pluggable modules), brownfield/ (safe migration detection). Must NOT reference D2. Covers FR-012 in README.md
- [X] T017 [P] [US4] Write Section "Development" (§16) — code blocks for running lint (`ruff check`), tests (`pytest`), type checking (`mypy`), and visualization (`dev-stack visualize`). Must NOT contain D2 references. Supports FR-017 (dual-audience flow: contributor section) in README.md
- [X] T018 [US4] Write Section "Spec Assets" (§17) — indented link lists grouped by spec directory: 001-dev-stack-ecosystem, 002-init-pipeline-enhancements, 003-codeboarding-viz, 004-vcs-best-practices. Each group links to its spec.md at minimum. Covers FR-013 in README.md

**Checkpoint**: Repository structure sections are complete — all directories, packages, and spec references accurate

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, D2 purge verification, and cross-section consistency

- [X] T019 Run D2 purge verification (SC-003): grep README.md for d2, D2, d2_gen, schema_gen, noodles, infra-console — must return zero matches in README.md
- [X] T020 Run CLI coverage verification (SC-001): compare `dev-stack --help` output against CLI Essentials table — every command must appear in both directions in README.md
- [X] T021 Run module coverage verification (SC-002): compare `ls src/dev_stack/modules/*.py` against Module Catalog table — all 9 modules present in README.md
- [X] T022 Run pipeline accuracy verification (SC-004): compare `build_pipeline_stages()` source against Pipeline table — 8 stages in correct order with correct gate modes in README.md
- [X] T023 Run repository layout verification (SC-006): compare Repository Layout tree against actual file system — zero missing significant directories in README.md
- [X] T024 Run spec references verification (SC-007): confirm specs/001, 002, 003, 004 all referenced in Spec Assets section in README.md
- [X] T025 Run optional deps verification (SC-008): confirm CodeBoarding, git-cliff, python-semantic-release, gh, glab, mypy, sphinx all marked Optional in Prerequisites table in README.md
- [X] T026 Run duplicate section check (FR-017): verify every `## ` heading appears exactly once — no topic covered in two places in README.md
- [X] T027 Final read-through: verify TOC anchor links resolve, code blocks use correct syntax, dual-audience flow (overview → install → usage → reference) is preserved, and README renders correctly in GitHub Markdown preview for README.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — can start immediately after foundational
- **US2 (Phase 4)**: Depends on Phase 2 — can start after Phase 2 (independent of US1 in theory, but same file so sequential in practice)
- **US3 (Phase 5)**: Depends on Phases 3 + 4 — enriches sections written in US1/US2
- **US4 (Phase 6)**: Depends on Phase 2 — can start after Phase 2 (independent of US1/US2/US3)
- **Polish (Phase 7)**: Depends on ALL user stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational → writes Prerequisites, Quickstart, Install, CLI, Validation sections
- **US2 (P1)**: After Foundational → writes Key Capabilities, Module Catalog, Pipeline, Visualization sections
- **US3 (P2)**: After US1 + US2 → enriches CLI, Module Catalog, Pipeline sections with VCS depth + writes Configuration
- **US4 (P2)**: After Foundational → writes Repository Layout, Architecture, Development, Spec Assets sections

### Single-File Constraint

Since all tasks edit `README.md`, true parallelism is limited. The [P] markers in Phase 6 indicate tasks that edit non-overlapping sections and could theoretically be batched. In practice, an LLM agent will execute tasks sequentially within each phase.

### Within Each User Story

- Write sections top-to-bottom (matching document order)
- Complete all sections before marking story checkpoint
- Commit after each phase or logical group

### Parallel Opportunities

**Phase 6 (US4)**: T015, T016, T017 edit independent non-adjacent sections — can be batched
**Phase 7 (Polish)**: T019–T025 are read-only verification tasks — can all run in parallel

---

## Parallel Example: Phase 7 Verification

```bash
# All verification tasks can run simultaneously:
Task T019: "grep -inE 'd2|d2_gen|schema_gen|noodles|infra.console' README.md"
Task T020: "diff <(dev-stack --help | grep commands) <(grep '|.*`dev-stack' README.md)"
Task T021: "ls src/dev_stack/modules/*.py vs Module Catalog rows"
Task T022: "grep stage names in README vs stages.py"
Task T023: "compare tree output vs Repository Layout section"
Task T024: "grep specs/001 specs/002 specs/003 specs/004 in README"
Task T025: "grep Optional for each optional tool in Prerequisites"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (backup + skeleton)
2. Complete Phase 2: Foundational (TOC + intro)
3. Complete Phase 3: User Story 1 (new user can init)
4. **STOP and VALIDATE**: New user can follow Prerequisites → Quickstart → Install → CLI → Validation
5. README is usable at this point even if incomplete

### Incremental Delivery

1. Phase 1 + 2 → Skeleton ready
2. Phase 3 (US1) → New users served → **MVP** ✅
3. Phase 4 (US2) → Returning users discover new features
4. Phase 5 (US3) → VCS depth enrichment
5. Phase 6 (US4) → Repo structure accurate
6. Phase 7 → Full verification → **Done** ✅

Each phase adds value without breaking previous phases. The README is functional after Phase 3.

---

## Notes

- All 27 tasks edit or verify a single file: `README.md`
- No test tasks generated (not requested in spec)
- VCS content is distributed per Clarification Q2 — US3 enriches sections written in US1/US2
- 7 duplicate sections from research.md are eliminated by writing consolidated sections from scratch
- D2 references are eliminated by never writing them (verified in T019)
- Commit after each phase completion
- Reference data-model.md entity tables for exact content (module names, stage order, command list, prerequisites)
- Reference contracts/readme-section-contract.md for section rules and validation criteria
