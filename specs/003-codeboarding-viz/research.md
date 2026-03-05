# Research: CodeBoarding Visualization

**Feature**: `003-codeboarding-viz`  
**Date**: 2026-03-04  
**Status**: Complete

## R-001: CodeBoarding CLI Invocation & Entry Point

**Task**: Determine the exact CLI command, entry point, and installation method for CodeBoarding.

**Findings**:
- CodeBoarding's `pyproject.toml` defines `[project.scripts] codeboarding = "main:main"`, confirming a `codeboarding` CLI entry point from the PyPI package.
- Invocation: `codeboarding --local <repo-path>` for local analysis.
- Installation: `pip install codeboarding` (or `pipx install codeboarding`), then `codeboarding-setup` to download LSP binaries to `~/.codeboarding/servers/`.
- User config stored at `~/.codeboarding/config.toml`.
- Requires Python >=3.12 (dev-stack requires >=3.11, no conflict since CodeBoarding is a separate tool).

**Decision**: Use `codeboarding --local .` as the subprocess command. Verify via `shutil.which("codeboarding")`.  
**Rationale**: The PyPI package provides the `codeboarding` CLI entry point. This matches the spec's FR-001.  
**Alternatives considered**: Running `python main.py` from a cloned repo — rejected because PyPI package is the supported distribution.

---

## R-002: Output Directory Structure (`.codeboarding/`)

**Task**: Determine the exact structure and contents of CodeBoarding's output directory.

**Findings**:
The `.codeboarding/` directory contains:

| File | Purpose |
|------|---------|
| `overview.md` | Top-level Mermaid architecture diagram + component descriptions with `[Expand]` links |
| `analysis.json` | Complete hierarchical component graph — the authoritative index |
| `analysis.json.lock` | Lock file for concurrent access |
| `analysis_manifest.json` | Metadata about the analysis run |
| `annotations.json` | Code annotations data |
| `codeboarding_version.json` | CodeBoarding version that produced this output |
| `file_coverage.json` | File coverage statistics |
| `health/` | Code health check results directory |
| `<Component_Name>.md` | Per-component Mermaid sub-diagram files (spaces → underscores in filename) |

**Key observation**: There is **no `output.json` file**. The spec (FR-002) assumed `.codeboarding/output.json` as the index. The actual index is `analysis.json`.

**Decision**: Use `analysis.json` as the index file for output discovery.  
**Rationale**: `analysis.json` contains the complete component hierarchy with names, descriptions, relations, and `component_id`s. Component markdown filenames can be derived from component names (spaces → underscores + `.md`).  
**Alternatives considered**: (a) Scanning `.codeboarding/*.md` via glob — rejected because it couples dev-stack to CodeBoarding's filename conventions without the structural context. (b) Parsing `overview.md` for `[Expand]` links — fragile, depends on markdown formatting.

**Spec impact**: FR-002 should reference `analysis.json` instead of `output.json`. The Assumptions section's mention of `output.json` should also be corrected.

---

## R-003: `analysis.json` Schema

**Task**: Document the structure of `analysis.json` for the output parser.

**Findings**:
```json
{
  "metadata": {
    "generated_at": "ISO-8601 timestamp",
    "repo_name": "string",
    "depth_level": 2,
    "file_coverage_summary": {
      "total_files": 0,
      "analyzed": 0,
      "not_analyzed": 0,
      "not_analyzed_by_reason": {}
    }
  },
  "description": "Repository-level description string",
  "components": [
    {
      "name": "Human Readable Name",
      "description": "Component description",
      "key_entities": [
        {
          "qualified_name": "module.Class",
          "reference_file": "path/to/file.py"
        }
      ],
      "assigned_files": ["path/to/file.py"],
      "source_cluster_ids": [3, 9],
      "component_id": "hex-string-16-chars",
      "can_expand": true,
      "components": [/* recursive sub-components at depth > 1 */],
      "components_relations": [
        {
          "relation": "verb phrase describing the relationship",
          "src_name": "Source Component",
          "dst_name": "Destination Component",
          "src_id": "hex-id",
          "dst_id": "hex-id"
        }
      ]
    }
  ],
  "components_relations": [
    {
      "relation": "description of top-level relationship",
      "src_name": "Source Component",
      "dst_name": "Destination Component",
      "src_id": "hex-id",
      "dst_id": "hex-id"
    }
  ]
}
```

**Key properties**:
- `components` is a recursive tree — sub-components appear when `can_expand: true` and `--depth-level >= 2`.
- `components_relations` exists at both the top level and within each component (for sub-component relations).
- `component_id` is a 16-character hex string, unique per component.
- Component markdown filename = component `name` with spaces replaced by underscores + `.md` (e.g., `"LLM Agent Core"` → `LLM_Agent_Core.md`).
- Ampersands and special chars in names also become underscores (e.g., `"Application Orchestrator & Repository Manager"` → `Application_Orchestrator_Repository_Manager.md`).

**Decision**: Parse `analysis.json` → extract component names and relations → derive `.md` filenames → extract Mermaid diagram from each `.md` file.  
**Rationale**: The JSON provides the structural index, and `.md` files contain the pre-rendered Mermaid diagrams. This two-step approach is resilient to changes in diagram format while using the stable JSON schema for discovery.

---

## R-004: Mermaid Diagram Format in Output Files

**Task**: Understand how Mermaid diagrams are embedded in CodeBoarding's markdown output.

**Findings**:
- `overview.md` contains a Mermaid code block (` ```mermaid ... ``` `) at the top, followed by a `## Details` section with component descriptions and `[Expand]` links.
- Per-component `.md` files follow the same pattern: Mermaid code block at top, then details.
- The Mermaid diagrams use `graph LR` (left-to-right flow) with component boxes linked by labeled arrows.
- Style annotations (CSS-like fills/strokes) are included for visual highlighting.

**Decision**: Extract the first ` ```mermaid ... ``` ` code block from each `.md` file for README injection.  
**Rationale**: The Mermaid block is always the first code block and is self-contained. Extracting just the diagram (not the Details section) keeps README injections clean.  
**Alternatives considered**: Generating our own Mermaid from `analysis.json` relations — rejected because CodeBoarding already produces polished, styled diagrams. Re-generating would lose styling and risk divergence.

---

## R-005: Default Depth Level Behavior

**Task**: Determine CodeBoarding's default `--depth-level` and reconcile with spec assumptions.

**Findings**:
- CodeBoarding README states: `--depth-level <int>` with **default: 1**.
- Depth 1 = top-level components only (the overview diagram).
- Depth 2 = top-level + one level of sub-components within each component.
- Higher depths produce more granular decomposition.
- The spec's clarification Q5 assumed "omitting depth restriction lets CodeBoarding produce all levels" — this is **incorrect**. Omitting `--depth-level` defaults to 1, producing only the top-level diagram.

**Impact on spec**:
- FR-007 states: "When omitted, no depth restriction is passed to CodeBoarding, allowing it to produce all levels by default." This needs correction.
- The Assumptions section states CodeBoarding's default produces "all decomposition levels" — incorrect.

**Decision**: When `--depth-level` is omitted from `dev-stack visualize`, pass `--depth-level 2` to CodeBoarding as the dev-stack default. This produces the top-level overview plus one level of sub-component diagrams — matching the spec's intent of generating per-folder sub-diagrams (User Story 2).  
**Rationale**: Depth 2 satisfies both User Story 1 (top-level diagram) and User Story 2 (per-folder sub-diagrams) out of the box. Depth 1 would leave User Story 2 unsatisfied. Passing no flag defaults to 1 which contradicts the spec's stated intent. A very large depth would be wasteful for most repos.  
**Alternatives considered**: (a) Default to depth 1 — rejected because sub-diagrams are a P2 requirement and should work by default. (b) Use a very large number (e.g., 99) to simulate "unlimited" — rejected as wasteful and unpredictable. (c) Omit the flag entirely — rejected because CodeBoarding's default (1) doesn't match our intent.

---

## R-006: Component-to-Folder Mapping for Sub-Diagram Injection

**Task**: Determine how to map CodeBoarding components to repository folders for README injection.

**Findings**:
- `analysis.json` components have `assigned_files` arrays listing files belonging to each component.
- A component's "folder" can be inferred as the common path prefix of its `assigned_files`.
- Example: Component with `assigned_files: ["agents/agent.py", "agents/constants.py", "agents/planner_agent.py"]` → folder = `agents/`.
- Some components span multiple directories (e.g., files in `monitoring/` and `main.py`).
- Top-level components map to the repo root for the overview diagram.

**Decision**: For each component, compute the longest common directory prefix of its `assigned_files`. If all files share a single directory, inject the sub-diagram into that directory's `README.md`. If files span multiple directories, inject into the narrowest common ancestor directory.  
**Rationale**: This provides sensible default placement without requiring CodeBoarding to emit folder mappings directly.  
**Alternatives considered**: (a) Use component names to find matching directories — fragile, names don't always match directory names. (b) Inject only at the repo root — loses the per-folder value of User Story 2. (c) Require the user to configure mappings — violates the Automation by Default principle.

---

## R-007: Incremental Mode Integration

**Task**: Understand CodeBoarding's `--incremental` flag behavior and integration with dev-stack's manifest.

**Findings**:
- CodeBoarding supports `--incremental` as a CLI flag.
- CodeBoarding also supports `--partial-component-id <id>` for re-analyzing specific components.
- CodeBoarding has its own internal change detection (Git-based diff analysis).
- dev-stack already has a `ManifestStore` with hash-based change tracking in `visualization/incremental.py`.

**Decision**: When `--incremental` is passed to `dev-stack visualize`, pass `--incremental` to CodeBoarding. Keep dev-stack's `ManifestStore` for its own change detection (to determine if CodeBoarding needs to be invoked at all), but delegate actual incremental analysis logic to CodeBoarding.  
**Rationale**: CodeBoarding's internal incremental engine is far more sophisticated than dev-stack's hash comparison. dev-stack's manifest serves as a first-pass gate (skip invocation entirely if nothing changed), while CodeBoarding handles the complex partial re-analysis.  
**Alternatives considered**: Using `--partial-component-id` with dev-stack's change detection — too complex, would require dev-stack to understand component boundaries.

---

## R-008: Error Handling & Timeout

**Task**: Confirm best practices for subprocess error handling and timeout configuration.

**Findings**:
- CodeBoarding uses LLM APIs (Google Gemini, Anthropic, OpenAI) requiring API keys set as environment variables.
- On missing API keys, CodeBoarding exits with non-zero status and descriptive stderr.
- CodeBoarding analysis can take several minutes for large repositories (LSP analysis + LLM calls).
- Python's `subprocess.run()` supports `timeout` parameter in seconds; raises `subprocess.TimeoutExpired` on timeout.

**Decision**: Use `subprocess.run()` with `timeout=300` (configurable via `--timeout`). On `TimeoutExpired`, capture partial output and display timeout message. On non-zero exit, display stderr verbatim. Consistent with spec FR-018 and FR-020.  
**Rationale**: Uniform error handling (all non-zero exits treated the same) is simpler to maintain and avoids coupling to CodeBoarding's internal error taxonomy.  

---

## R-009: Injection Ledger Format

**Task**: Design the injection ledger file format for tracking README injections.

**Findings**:
- The ledger must track which README files were modified and what marker IDs were used.
- Multiple marker types exist: `architecture` (root), `component-architecture` (sub-folders).
- The ledger must support idempotent updates (re-running visualization updates the ledger).

**Decision**: Use `.codeboarding/injected-readmes.json` with the following format:
```json
{
  "version": 1,
  "generated_at": "ISO-8601",
  "entries": [
    {
      "readme_path": "README.md",
      "marker_id": "architecture",
      "component_name": null
    },
    {
      "readme_path": "agents/README.md",
      "marker_id": "component-architecture",
      "component_name": "LLM Agent Core"
    }
  ]
}
```
**Rationale**: Explicit entries with marker IDs support targeted cleanup during uninstall. The version field allows future format migration. Using `null` for the root component distinguishes it from named components.

---

## Summary of Spec Corrections Needed

| Spec Reference | Issue | Correction |
|----------------|-------|------------|
| FR-002 | References `output.json` | Should reference `analysis.json` |
| FR-007 | "no depth restriction" when omitted | dev-stack should default to `--depth-level 2`; CodeBoarding's default is 1 |
| Assumptions #3 | Mentions `output.json` | Should reference `analysis.json` |
| Assumptions #4 | Says `--depth-level` maps to CB flags | Correct, but note CB default is 1, not unlimited |
| Clarification Q1 | Mentions `output.json` | Should say `analysis.json` |
| Clarification Q5 | Says CB default produces all levels | CB default is depth=1 (top-level only) |
