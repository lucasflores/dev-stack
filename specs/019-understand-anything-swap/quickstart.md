# Quickstart: Replace Codeboarding With Understand-Anything

**Feature**: `019-understand-anything-swap`

## Goal

Use Understand-Anything as the only supported repository graph workflow, keep committed graph artifacts fresh, and enforce freshness in both local hooks and required CI checks.

## Supported Interactive Plugin Experiences

- VS Code + GitHub Copilot plugin workflow
- Claude Code plugin workflow

Required interaction checks for each supported experience:

1. Open the interactive graph dashboard.
2. Search for a known node by name.
3. Inspect node relationships in the graph UI.

Expected result:
- All three interaction checks pass on each supported plugin experience.

## 1. Install and initialize Understand-Anything

1. Install/plugin-enable Understand-Anything in your coding agent environment.
2. From repository root, run the initial analysis flow (for example `/understand`) to build `.understand-anything/knowledge-graph.json`.
3. Verify that `.understand-anything/knowledge-graph.json` includes project metadata (`analyzedAt`, `gitCommitHash`) and graph nodes.

Expected result:
- `.understand-anything/knowledge-graph.json` exists and is valid JSON.

## 2. Commit artifact policy-compliant graph outputs

1. Add `.understand-anything/` artifacts to version control.
2. Exclude local scratch outputs:
   - `.understand-anything/intermediate/`
   - `.understand-anything/diff-overlay.json`
3. If any committed `.understand-anything/*.json` exceeds 10 MB, configure Git LFS tracking for that path pattern.
4. For existing repositories, verify migration compliance by removing stale `.codeboarding/` artifact references and confirming only `.understand-anything/` artifact policy remains.

Expected result:
- Graph artifacts are committed with correct exclusion and storage policy.

## 3. Run local freshness validation

1. Make a graph-impacting code change.
2. Run local validation through the existing visualize entrypoint.
3. If validation reports stale/indeterminate graph state, refresh the graph using iterative Understand-Anything flow (for example `/understand --auto-update` or rerun `/understand`).
4. Re-run validation and confirm pass.

Expected result:
- Local pre-commit path blocks stale graph state and passes after refresh.

## 4. Validate required CI behavior

1. Push the branch and open a pull request.
2. Confirm required CI graph freshness check executes with check name `dev-stack-graph-freshness` (or documented equivalent mapped check name).
3. For stale graph artifacts, confirm CI fails with actionable remediation.
4. After refreshing and committing artifacts, confirm CI passes.

Expected result:
- CI behaves as required merge gate for graph freshness.

## 4a. Configure Required Branch Protection Check

1. Open repository branch protection settings for protected branches.
2. Add `dev-stack-graph-freshness` as a required status check (or document the repository-specific mapped check name).
3. Validate that merge is blocked when this check is failing or missing.
4. Validate that merge is allowed when this check passes.

Expected result:
- Branch protection enforces required graph freshness validation for mergeability.

## 5. Confirm Codeboarding removal and README policy

1. Search the repo for active Codeboarding references in automation and docs.
2. Verify architecture guidance points only to Understand-Anything interactive graph workflow.
3. Confirm README files no longer depend on generated static diagram injection markers.

Expected result:
- Single-tool visualization policy is enforced and documented.

## 6. SC-004 Sampling Protocol

1. Gather a sample of at least 10 contributors over a 30-day window.
2. For each sampled contributor, capture whether they can find architecture relationships via the interactive graph without README-embedded diagrams.
3. Compute success rate as `successful contributors / sampled contributors`.
4. Confirm success rate is at least 90%.

Expected result:
- SC-004 measurement is repeatable and auditable.

### SC-004 Reporting Template

Use this table for each 30-day measurement window:

| Contributor | Date | Plugin Experience | Open Dashboard | Search Node | Inspect Relationships | Success (Y/N) | Notes |
|-------------|------|-------------------|----------------|-------------|-----------------------|---------------|-------|
| example-1   | YYYY-MM-DD | copilot | Y | Y | Y | Y | baseline |

Aggregate summary template:

| Window Start | Window End | Sample Size | Successful Contributors | Success Rate | Meets >= 90% |
|--------------|------------|-------------|-------------------------|--------------|--------------|
| YYYY-MM-DD   | YYYY-MM-DD | 10+         | N                       | N / sample   | Y/N          |

## Validation Checklist

- `dev-stack visualize` no longer depends on Codeboarding CLI.
- `.understand-anything/knowledge-graph.json` is present and parseable.
- Graph freshness checks block stale or indeterminate graph state locally.
- Required CI check `dev-stack-graph-freshness` (or documented equivalent mapped name) blocks merge when graph policy fails.
- Git LFS rule is present whenever committed graph JSON exceeds 10 MB.
- No active Codeboarding workflow guidance remains in project docs.
- All supported plugin experiences pass open/search/relationship interaction checks.

## Migration Compliance Checklist (Existing Repositories)

- [ ] Legacy `.codeboarding/` artifacts removed from tracked project paths.
- [ ] `.understand-anything/knowledge-graph.json` exists and is committed.
- [ ] `.understand-anything/intermediate/` and `.understand-anything/diff-overlay.json` are excluded from committed artifacts.
- [ ] Graph-impacting source changes include synchronized updates to committed graph artifacts.
- [ ] Branch protection requires `dev-stack-graph-freshness` (or documented mapped equivalent check name).
- [ ] CI and local pre-commit freshness validation both pass after migration.
