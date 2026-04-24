# Research: Update APM Default Packages and Manifest Version

**Feature**: 020-update-apm-defaults  
**Date**: 2026-04-24  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Finding 1: APM path-specific package syntax

**Decision**: Use `owner/repo/path/to/item` string entries in `dependencies.apm`

**Rationale**: The APM CLI resolves each entry by cloning the repo and copying the specified sub-path into the appropriate `.github/` directory. The path suffix acts as a selector — no special YAML syntax is required.

**Verification**: Live `apm install` test in `/tmp/apm-test-14973` confirmed:
- `lucasflores/agent-skills/agents/idea-to-speckit.agent.md` → `.github/agents/` (1 agent integrated)
- `lucasflores/agent-skills/prompts/AutoSpecKit.prompt.md` → `.github/prompts/` + `.claude/commands/` (1 prompt + 1 command)
- `lucasflores/agent-skills/skills/commit-pipeline` → `.github/skills/` (1 skill integrated)
- `lucasflores/agent-skills/skills/dev-stack-update` → `.github/skills/` (1 skill integrated)
- Exit code: 0. All 4 dependencies installed successfully.

**Alternatives considered**:
- Object-style `{package: owner/repo, paths: [...]}` — **rejected**: APM CLI returns parse error "Object-style dependency must have a 'git' or 'path' field"
- Single `owner/repo` package entry — **rejected**: installs the full repo, not the specific files requested

---

## Finding 2: Empty `mcp` key behavior in merged manifests

**Decision**: Omit the `mcp` key entirely if the merged `mcp` list resolves to empty

**Rationale**: Writing `mcp: []` into the manifest is noise. It misleads readers into thinking MCP server declarations are expected, and causes the FR-006 acceptance test ("no `mcp` key in merged manifest") to fail trivially. Omitting the key keeps the file clean and unambiguous.

**Implementation note**: The current `_merge_manifest` always writes `deps["mcp"] = mcp_list` back. With `DEFAULT_SERVERS = ()` and no existing entries, `mcp_list` would be `[]`. The fix: only write `deps["mcp"]` if `mcp_list` is non-empty; delete it if it exists and would become empty.

**Alternatives considered**:
- Write `mcp: []` — **rejected**: noise, contradicts spec intent, fails acceptance test
- Remove `mcp` from all merged manifests regardless of existing content — **rejected**: would destroy user's existing MCP declarations (Brownfield Safety violation)

---

## Finding 3: Deduplication key for path-specific `apm` entries

**Decision**: Full path before any `#` pin suffix (e.g., `lucasflores/agent-skills/skills/commit-pipeline`)

**Rationale**: The existing `split("#")[0]` logic in `_merge_manifest` is already correct syntactically. The old behavior was a coincidental bug: when `DEFAULT_APM_PACKAGES` contained only `"lucasflores/agent-skills"`, the key `"lucasflores/agent-skills"` would match any pinned variant. With path-specific entries, the full path before `#` is the only sensible key — each path represents a distinct installable artifact.

**No code change required**: The dedup logic `name.split("#")[0]` and `pkg.split("#")[0]` are unchanged. The behavior change comes entirely from `DEFAULT_APM_PACKAGES` now containing full paths. Two entries from the same repo but at different paths will correctly be treated as distinct.

**Alternatives considered**:
- Repo-prefix dedup (`owner/repo`) — **rejected**: would treat all four new entries as duplicates of each other if any one were already present

---

## Finding 4: Manifest template version

**Decision**: `2.0.0`

**Rationale**: Removing all MCP server defaults is a breaking change — projects that relied on MCP servers being auto-added will no longer get them. A major version bump communicates this clearly and makes the change visible in `git diff` / PR review.

**Alternatives considered**:
- `1.1.0` — **rejected**: minor version suggests additive change; removing defaults is breaking
- `1.0.1` — **rejected**: patch version suggests a bug fix; this is intentional behavioral change

---

## Finding 5: `_parse_install_result` success message

**Decision**: `"All APM dependencies installed successfully"`

**Rationale**: The module no longer manages MCP servers as its primary purpose. The old message `"All MCP servers installed successfully"` is factually wrong post-change (the module now installs agents, prompts, and skills). The new message is accurate for any mix of APM dependency types.

---

## Finding 6: Class docstring

**Decision**: `"Manage APM packages and agent skills via the APM CLI."`

**Rationale**: Accurately describes post-change behavior. Removes the stale "MCP server management" framing.

---

## Summary Table

| Requirement | Resolution | Verified |
|-------------|-----------|---------|
| Path-specific APM syntax | `owner/repo/path/to/item` string entries | ✅ Live install test |
| Empty `mcp` key in merge | Omit key entirely | ✅ Logic traced through `_merge_manifest` |
| Dedup key for path entries | Full path before `#` | ✅ No code change needed |
| Manifest version | `2.0.0` | ✅ Agreed |
| Success message | `"All APM dependencies installed successfully"` | ✅ Agreed |
| Class docstring | `"Manage APM packages and agent skills via the APM CLI."` | ✅ Agreed |
