# Implementation Plan: Update APM Default Packages and Manifest Version

**Branch**: `020-update-apm-defaults` | **Date**: 2026-04-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/020-update-apm-defaults/spec.md`

## Summary

Remove all MCP server defaults from the APM module and template; replace the single pinned `lucasflores/agent-skills` package with four path-specific entries pointing to exactly the agents, prompts, and skills the project needs. Bump the manifest template version to `2.0.0`. Fix merge deduplication to use the full path key. Update stale success message and class docstring. Adjust all tests that asserted old defaults.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyYAML, packaging, click (all existing; no new deps)  
**Storage**: Files only — `src/dev_stack/templates/apm/default-apm.yml`, in-module constants  
**Testing**: pytest  
**Target Platform**: Linux/macOS developer workstation (wherever dev-stack init runs)  
**Project Type**: Single Python package (single project)  
**Performance Goals**: N/A — no runtime performance impact  
**Constraints**: Must not modify or remove existing MCP entries in brownfield manifests; `apm install` on the new template must exit 0 (verified)  
**Scale/Scope**: 3 source files modified, ~14 test cases updated or added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First | ✅ Pass | No CLI surface change; all behavior flows through existing `install`/`update`/`preview` commands |
| II. Spec-Driven | ✅ Pass | `spec.md` authored and clarified before any implementation |
| III. Automation by Default | ✅ Pass | No pipeline changes required; pre-commit suite still runs unchanged |
| IV. Brownfield Safety | ✅ Pass | Merge strategy preserves existing entries; does not remove user's existing MCP servers |
| V. AI-Native Architecture | ✅ Pass | MCP servers remain user-installable; defaults shift to agent skills — still AI-native, more targeted |
| VI. Local-First | ✅ Pass | No change to local/CI split |
| VII. Observability | ✅ Pass | Stale success message updated (FR-009); docstring updated (FR-010) |
| VIII. Modularity | ✅ Pass | Only APM module touched; no other module affected |

**GATE RESULT: All pass. Proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/020-update-apm-defaults/
├── plan.md          ← this file
├── research.md      ← Phase 0 output (below)
├── data-model.md    ← Phase 1 output
├── quickstart.md    ← Phase 1 output
├── contracts/       ← Phase 1 output (no API surface — omitted)
└── tasks.md         ← /speckit.tasks output (not created here)
```

### Source Code (repository root)

```text
src/dev_stack/
├── templates/apm/
│   └── default-apm.yml          ← MODIFY: version bump, remove mcp, update apm entries
└── modules/
    └── apm.py                   ← MODIFY: docstring, DEFAULT_SERVERS, DEFAULT_APM_PACKAGES,
                                             _merge_manifest, _parse_install_result

tests/
├── contract/
│   └── test_apm_contract.py     ← NO CHANGE (protocol compliance only; no defaults assertions)
├── integration/
│   └── test_apm_install.py      ← MODIFY: update MCP merge count assertion
└── unit/
    └── test_apm_module.py       ← MODIFY: 8 test cases updated; 2 new test cases added
```

**Structure Decision**: Single Python project layout. All changes contained within the `apm` module and its test files. No new files created.

## Complexity Tracking

*No Constitution Check violations — table omitted.*

---

## Phase 0: Research

> See [research.md](research.md) for full findings.

All unknowns were resolved prior to spec authoring via a live `apm install` test in an isolated directory. No open questions remain.

**Key findings:**

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Path-specific syntax `owner/repo/path/to/item` | Confirmed working via live install — installs each artifact to the correct `.github/` subdirectory | Object-style `{package: ..., paths: [...]}` — rejected: APM CLI rejects with "must have a 'git' or 'path' field" |
| Empty `mcp:` key omitted (not written as `mcp: []`) | Keeps manifest clean; merge acceptance test passes trivially | Write `mcp: []` — rejected: adds noise and confuses manual readers |
| Deduplication by full path before `#` | Each path is a distinct artifact; repo-only dedup silently drops entries 2–4 | Repo-prefix dedup — rejected: breaks multi-entry installs from same repo |
| Version `2.0.0` | Breaking change in defaults; major bump communicates that clearly | `1.1.0` — rejected: defaults removal is a breaking change, not a minor addition |

---

## Phase 1: Design

### Data Model

> See [data-model.md](data-model.md) for full entity definitions.

No new entities. Two existing in-memory structures change:

| Field | Old Value | New Value |
|-------|-----------|-----------|
| `APMModule.DEFAULT_SERVERS` | `("io.github.upstash/context7", "io.github.github/github-mcp-server", "huggingface/hf-mcp-server")` | `()` |
| `APMModule.DEFAULT_APM_PACKAGES` | `("lucasflores/agent-skills",)` | `("lucasflores/agent-skills/agents/idea-to-speckit.agent.md", "lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md", "lucasflores/agent-skills/skills/commit-pipeline", "lucasflores/agent-skills/skills/dev-stack-update")` |

Template file change:

| Field | Old | New |
|-------|-----|-----|
| `version` | `"1.0.0"` | `"2.0.0"` |
| `dependencies.mcp` | 3 server entries | *(key removed entirely)* |
| `dependencies.apm` | 1 pinned package | 4 path-specific entries |

### Contracts

No public API surface changes. `install()`, `update()`, `verify()`, `preview_files()`, and `audit()` signatures are unchanged. The only observable contract changes are:

- `_parse_install_result` success message: `"All MCP servers installed successfully"` → `"All APM dependencies installed successfully"`
- `APMModule.__doc__`: `"Manage MCP servers via the APM CLI."` → `"Manage APM packages and agent skills via the APM CLI."`

> No OpenAPI/GraphQL contracts needed — this feature has no HTTP surface. `contracts/` directory intentionally empty.

### Quickstart

> See [quickstart.md](quickstart.md) for developer verification steps.

### Implementation Changeset

#### 1. `src/dev_stack/templates/apm/default-apm.yml`

```yaml
# BEFORE
name: "{{ PROJECT_NAME }}"
version: "1.0.0"
dependencies:
  mcp:
    - io.github.upstash/context7
    - io.github.github/github-mcp-server
    - huggingface/hf-mcp-server
  apm:
    - lucasflores/agent-skills#8434caf3f85dabb8df197185f449fea1488406ec

# AFTER
name: "{{ PROJECT_NAME }}"
version: "2.0.0"
dependencies:
  apm:
    - lucasflores/agent-skills/agents/idea-to-speckit.agent.md
    - lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md
    - lucasflores/agent-skills/skills/commit-pipeline
    - lucasflores/agent-skills/skills/dev-stack-update
```

#### 2. `src/dev_stack/modules/apm.py` — module-level changes

| Location | Change |
|----------|--------|
| Class docstring | `"Manage MCP servers via the APM CLI."` → `"Manage APM packages and agent skills via the APM CLI."` |
| `DEFAULT_SERVERS` | `(3 servers)` → `()` |
| `DEFAULT_APM_PACKAGES` | `("lucasflores/agent-skills",)` → `(4 path entries)` |
| `_parse_install_result` success | `"All MCP servers installed successfully"` → `"All APM dependencies installed successfully"` |

#### 3. `src/dev_stack/modules/apm.py` — `_merge_manifest` logic

Two targeted logic changes:

**a) Omit `mcp` key when result is empty (FR-006):**

```python
# BEFORE
deps["mcp"] = mcp_list

# AFTER
if mcp_list:
    deps["mcp"] = mcp_list
elif "mcp" in deps:
    del deps["mcp"]
```

**b) Deduplication key uses full path before `#` (FR-008):**

```python
# BEFORE
existing_apm_names.add(name.split("#")[0])
# and dedup check:
if pkg.split("#")[0] not in existing_apm_names:

# AFTER — identical logic, semantics change comes from DEFAULT_APM_PACKAGES now
# containing full paths; the split("#")[0] correctly compares
# "lucasflores/agent-skills/skills/commit-pipeline" == "lucasflores/agent-skills/skills/commit-pipeline"
# rather than the old bare "lucasflores/agent-skills" == "lucasflores/agent-skills"
```

No code change needed to `_merge_manifest` for dedup — the logic is already correct (`split("#")[0]`). The behavior change is entirely driven by the new `DEFAULT_APM_PACKAGES` values. ✅

#### 4. `tests/unit/test_apm_module.py` — test case updates

| Test class | Method | Change |
|-----------|--------|--------|
| `TestBootstrapManifest` | `test_create_when_missing` | Assert `"mcp" not in content["dependencies"]`; `len(apm) == 4` |
| `TestBootstrapManifest` | `test_overwrite_when_exists` | Same assertion as above |
| `TestBootstrapManifest` | `test_force_overwrites_existing` | Same assertion as above |
| `TestBootstrapManifest` | `test_merge_adds_missing_defaults` | Remove MCP-count assertion; assert `len(apm) == 4` added to existing manifest with no prior `apm` section |
| `TestExpandedTemplate` | `test_template_contains_mcp_and_apm_sections` | Assert `"mcp" not in content["dependencies"]`; `"apm" in content["dependencies"]` |
| `TestExpandedTemplate` | `test_template_preserves_all_mcp_servers` | Replace with `test_template_has_no_mcp_servers`: assert `"mcp" not in content["dependencies"]` |
| `TestExpandedTemplate` | `test_template_contains_agent_skills` | Assert `len(apm_list) == 4`; check all four paths present |
| `TestMergeManifestApm` | `test_merge_adds_apm_section_to_existing_manifest` | Assert `len(apm) == 4` (not 1) |
| `TestMergeManifestApm` | `test_merge_does_not_duplicate_existing_apm_packages` | Update to use path-specific entry for dedup check |
| `TestMergeManifestApm` | `test_merge_preserves_custom_apm_packages` | Assert `len(apm_list) == 5` (custom + 4 defaults) |
| *(new)* | `test_merge_empty_mcp_key_omitted` | Given manifest with no mcp, after merge: `"mcp" not in content["dependencies"]` |
| *(new)* | `test_merge_no_mcp_added_even_when_empty` | Confirm DEFAULT_SERVERS is empty and merge never adds mcp entries |

#### 5. `tests/integration/test_apm_install.py` — test case updates

| Test class | Method | Change |
|-----------|--------|--------|
| `TestCommunityPackages` | `test_merge_preserves_community_packages` | Assert `len(mcp_list) == 1` (community only; no defaults added) |

### Constitution Check (Post-Design)

Re-evaluated after Phase 1 design:

| Principle | Status | Notes |
|-----------|--------|-------|
| IV. Brownfield Safety | ✅ Pass | `_merge_manifest` preserves all user MCP entries; only omits the key if the merged result is genuinely empty |
| VIII. Modularity | ✅ Pass | 0 cross-module coupling changes |

**GATE RESULT: All pass. Ready for `/speckit.tasks`.**
