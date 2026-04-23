# Research: Replace Codeboarding With Understand-Anything

**Feature**: `019-understand-anything-swap`  
**Date**: 2026-04-22

## R-001: Canonical Graph Artifact Location and Sharing Model

**Decision**: Treat `.understand-anything/knowledge-graph.json` as the canonical committed graph artifact, and commit `.understand-anything/*` except `.understand-anything/intermediate/` and `.understand-anything/diff-overlay.json`.

**Rationale**: Understand-Anything documents this exact sharing model for team onboarding and review workflows. It aligns with the clarified requirement that teammates can consume a committed graph without rerunning the full initial pipeline.

**Alternatives considered**:
- Local-only graph artifacts: rejected because it breaks teammate reuse and required CI validation parity.
- Commit only a lightweight manifest: rejected because it diverges from upstream Understand-Anything guidance.

---

## R-002: Incremental and Diff-Based Graph Impact Detection

**Decision**: Implement graph-impact detection using Understand-Anything-derived signals in this order: (1) consume local diff-overlay style output when present, (2) otherwise evaluate changed paths against committed graph node `filePath` entries from `knowledge-graph.json`, (3) fail closed as indeterminate when artifacts are missing or malformed.

**Rationale**: This preserves the clarified requirement to use Understand-Anything incremental/diff semantics while remaining deterministic in hooks and CI environments that cannot execute interactive slash commands directly.

**Alternatives considered**:
- Path-extension heuristics only: rejected due high false-positive/false-negative risk.
- Always requiring full graph regeneration for every commit: rejected as too slow and contrary to iterative workflow goals.

---

## R-003: Enforcement Topology (Local + CI)

**Decision**: Enforce graph freshness in both local pre-commit flow and CI workflow templates, with CI configured as a required merge condition.

**Rationale**: Local hooks provide immediate feedback; CI provides tamper-resistant enforcement when hooks are skipped or not installed.

**Alternatives considered**:
- Local-only enforcement: rejected due bypass risk.
- CI-only enforcement: rejected due slower contributor feedback and poorer developer experience.

---

## R-004: README and Documentation Policy

**Decision**: Remove static architecture diagram injection from README flows and replace visualization guidance with an interactive Understand-Anything graph workflow.

**Rationale**: The specification explicitly requires no embedded README diagrams and a single graphing approach.

**Alternatives considered**:
- Keep static fallback diagrams: rejected because it reintroduces dual-tool drift.
- Remove all visualization docs: rejected because onboarding and adoption clarity would regress.

---

## R-005: Graph Storage Threshold and Git LFS

**Decision**: Use regular Git by default for committed graph JSON and require Git LFS tracking when any committed `.understand-anything/*.json` artifact exceeds 10 MB.

**Rationale**: Matches clarified requirement and upstream guidance while avoiding unnecessary LFS complexity for small repositories.

**Alternatives considered**:
- Always use LFS: rejected as unnecessary friction for most repos.
- Never use LFS: rejected due repository bloat and clone performance risks for larger graphs.

---

## R-006: Backward-Compatible CLI Surface

**Decision**: Keep `dev-stack visualize` and the `visualization` module contract, but migrate internals from Codeboarding-specific runners/parsers to Understand-Anything artifact validation and policy checks.

**Rationale**: Minimizes breaking changes across existing hooks, automation, and user habits while still removing Codeboarding from implementation and docs.

**Alternatives considered**:
- Rename command/module to new graph-specific names now: rejected because migration blast radius is larger and unnecessary for this feature.

---

## R-007: CI Feasibility Without Interactive Plugin Runtime

**Decision**: Do not require interactive Understand-Anything runtime invocation in CI. CI validates committed artifacts, graph-impact alignment, and storage policy from repository state only.

**Rationale**: Understand-Anything is primarily plugin/skill-driven in agent environments rather than a guaranteed standalone binary in headless CI.

**Alternatives considered**:
- Execute plugin commands in CI directly: rejected because no stable, repository-agnostic shell command surface is guaranteed.
- Skip CI validation entirely: rejected due clarified requirement for required CI enforcement.
