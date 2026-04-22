# Feature Specification: Soften Sphinx `-W` for Brownfield Projects

**Feature Branch**: `[001-soften-sphinx-warnings]`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "Soften Sphinx `-W` for Brownfield Projects"

## Clarifications

### Session 2026-04-21

- Q: Which source of truth should control docs warning strictness at runtime for both pipeline execution and generated docs defaults? -> A: Use `[tool.dev-stack.pipeline] strict_docs` in `pyproject.toml` as the canonical source; brownfield init sets `strict_docs = false`, greenfield remains strict by default.
- Q: For non-strict mode (`strict_docs = false`), what exact default should generated docs Makefile use for `SPHINXOPTS`? -> A: Emit `SPHINXOPTS ?=` (empty value).
- Q: Should this feature include the optional brownfield strict opt-in control now (for example a pipeline flag that forces strict docs), or defer it? -> A: Defer strict opt-in control to a separate follow-up spec.
- Q: For repositories with an existing `docs/Makefile` generated before this change, what behavior should this feature require? -> A: No automatic migration; only newly generated or explicitly regenerated Makefiles get the new default.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Unblock Brownfield Docs Validation (Priority: P1)

As a developer running the pipeline on a brownfield repository, I need documentation warnings to be reported without failing the docs stage so the pipeline can complete and still surface actionable feedback.

**Why this priority**: Brownfield projects currently hard-fail on inherited documentation debt, which blocks downstream stages and prevents commit output.

**Independent Test**: Run the pipeline with `strict_docs = false` (brownfield default or explicit override) where docs produce warnings but no build-breaking errors; verify docs validation reports warnings and at least one stage after docs-api is executed.

**Acceptance Scenarios**:

1. **Given** `strict_docs = false` and documentation build output contains warnings only, **When** the docs-api stage runs, **Then** warnings are reported, docs-api completes without hard-fail, and at least one subsequent stage is executed.
2. **Given** `strict_docs = false` and documentation build output contains actual build errors, **When** the docs-api stage runs, **Then** the stage fails as a hard gate.

---

### User Story 2 - Preserve Greenfield Strictness (Priority: P2)

As a developer working in a greenfield repository, I need docs warnings to remain strict so newly scaffolded projects keep documentation quality expectations from day one.

**Why this priority**: This prevents quality regressions in projects that are expected to be warning-clean.

**Independent Test**: Run the docs-api stage with `strict_docs = true` (greenfield default or explicit override) on a warnings fixture and verify failure; run it on a warning-free fixture and verify pass.

**Acceptance Scenarios**:

1. **Given** `strict_docs = true`, **When** docs build output includes warnings, **Then** the docs-api stage fails.
2. **Given** `strict_docs = true`, **When** docs build output has no warnings or errors, **Then** the docs-api stage passes.

---

### User Story 3 - Mode-Aware Docs Scaffold Defaults (Priority: P3)

As a developer initializing docs support, I need generated docs defaults to match project origin so I do not have to manually patch strictness settings after initialization.

**Why this priority**: Prevents repetitive manual edits and keeps generated defaults aligned with expected pipeline behavior.

**Independent Test**: Initialize one brownfield fixture and one greenfield fixture, then compare generated docs defaults to confirm each mode receives the expected warning policy.

**Acceptance Scenarios**:

1. **Given** a brownfield initialization flow with no explicit `strict_docs` value already configured, **When** docs scaffolding is generated, **Then** the default docs options omit fatal-warning behavior.
2. **Given** a greenfield initialization flow with no explicit `strict_docs` value already configured, **When** docs scaffolding is generated, **Then** the default docs options include fatal-warning behavior.
3. **Given** `strict_docs = false`, **When** `docs/Makefile` is generated, **Then** it sets `SPHINXOPTS ?=` by default.

---

### Edge Cases

- Deletion of the transient brownfield initialization marker after first commit must not change behavior once `strict_docs` has been persisted.
- If `pyproject.toml` is missing, unreadable, or omits `strict_docs`, docs strictness falls back to strict mode by default.
- Explicit `strict_docs` values override inferred brownfield or greenfield provenance.
- For repositories missing `docs/` or Sphinx tooling, docs-api retains existing skip behavior.
- Existing `docs/Makefile` files created before this change are not auto-migrated by pipeline execution.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine docs warning strictness from `[tool.dev-stack.pipeline] strict_docs` in `pyproject.toml` as the canonical runtime source for both docs-api stage behavior and generated docs defaults.
- **FR-002**: When `strict_docs = false`, the docs-api stage MUST treat documentation warnings as non-fatal.
- **FR-003**: When `strict_docs = true`, the docs-api stage MUST treat documentation warnings as fatal.
- **FR-004**: The docs-api stage MUST fail on actual documentation build errors regardless of project origin.
- **FR-005**: Generated docs scaffolding defaults MUST be mode-aware: non-strict defaults MUST emit `SPHINXOPTS ?=` (empty), while strict defaults MUST emit `SPHINXOPTS ?= -W --keep-going`.
- **FR-006**: If `pyproject.toml` is missing, unreadable, or omits `strict_docs`, the system MUST default to strict behavior (`strict_docs = true`).
- **FR-007**: Brownfield warning policy persistence MUST be achieved via `strict_docs` configuration and MUST NOT depend solely on a one-time initialization marker.
- **FR-010**: An explicit `strict_docs` value in `pyproject.toml` MUST take precedence over inferred project provenance.
- **FR-008**: The feature MUST include automated test coverage for both brownfield and greenfield behavior in pipeline execution and docs scaffolding generation.
- **FR-009**: The change MUST be limited to docs warning strictness behavior and MUST NOT broaden scope into Sphinx extension tuning, package layout detection, unrelated docs configuration changes, or new CLI flags for strictness control.
- **FR-011**: The feature MUST NOT automatically rewrite pre-existing `docs/Makefile` files during normal pipeline execution.
- **FR-012**: The new Makefile strictness default MUST apply to newly generated scaffolds and explicit regeneration flows only.
- **FR-013**: Docs-api stage skip behavior for missing `docs/` directory or missing Sphinx tooling MUST remain unchanged.

### Key Entities *(include if feature involves data)*

- **Project Origin Profile**: A classification of repository context (brownfield, greenfield, or unknown) used to decide default docs strictness.
- **Docs Strictness Policy**: The effective warning-handling policy for docs validation and scaffold defaults (strict/fatal warnings vs non-strict warnings).
- **Docs Validation Outcome**: Stage-level result that distinguishes warning-only builds from true build failures and maps each to pass/fail behavior.
- **Scaffolded Docs Defaults**: Generated docs options applied during initialization so docs behavior is consistent with origin policy.

## Assumptions

- Brownfield projects commonly contain inherited documentation warnings that are outside immediate feature work and should not block pipeline progress by default.
- Greenfield projects initialized by dev-stack are expected to maintain warning-clean documentation and therefore remain strict by default.
- Brownfield initialization sets `strict_docs = false` in `pyproject.toml` unless already explicitly configured.
- Existing repositories without persistent origin metadata should favor safety by using strict behavior.

## Dependencies

- Availability of `pyproject.toml` and `[tool.dev-stack.pipeline] strict_docs` parsing in both pipeline and docs scaffolding flows.
- Existing pipeline stage gating behavior (hard-fail vs pass/skip semantics) remains unchanged outside docs warning strictness.
- Test fixtures or mocks representing both brownfield and greenfield repository modes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In `strict_docs = false` validation scenarios with warnings only, 100% of docs-api runs complete without hard-fail and record execution of at least one stage after docs-api.
- **SC-002**: In validation scenarios with true documentation build errors (both `strict_docs = false` and `strict_docs = true`), 100% of docs-api runs fail as hard gates.
- **SC-003**: In `strict_docs = true` validation scenarios with documentation warnings, 100% of docs-api runs fail.
- **SC-004**: In initialization tests, generated docs defaults match strictness expectations in 100% of cases (`strict_docs = false` -> `SPHINXOPTS ?=`; `strict_docs = true` -> `SPHINXOPTS ?= -W --keep-going`).
- **SC-005**: Regression tests confirm no behavior change to non-docs pipeline stages for this feature.
- **SC-006**: In migration behavior tests, existing `docs/Makefile` files are unchanged during normal pipeline execution in 100% of cases.
