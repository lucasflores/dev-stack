# Quickstart — Verification Playbook

**Feature**: 005-readme-update  
**Date**: 2026-03-09

## Purpose

Step-by-step verification script to confirm the updated README satisfies all eight success criteria.

---

## Pre-flight

```bash
cd /path/to/dev-stack
git checkout 005-readme-update
```

---

## SC-001: CLI Command Coverage

```bash
# Extract documented commands from README
grep -oP '^\|\s*`([a-z-]+\s?[a-z]*)`' README.md | sort -u > /tmp/readme-cmds.txt

# Extract actual CLI commands
dev-stack --help | grep -oP '^\s+([a-z-]+)' | sort -u > /tmp/actual-cmds.txt

# Diff — expect empty output
diff /tmp/readme-cmds.txt /tmp/actual-cmds.txt
```

**Pass criteria**: Diff is empty. All 12 commands (init, update, rollback, mcp, pipeline, visualize, status, changelog, hooks, pr, release, version) appear.

---

## SC-002: Module Catalog Coverage

```bash
# Extract module filenames from source
ls src/dev_stack/modules/*.py | grep -v __init__ | sed 's|.*/||;s|\.py||' | sort > /tmp/actual-modules.txt

# Count documented module rows in README
grep -cP '^\|.*\|.*\|.*\|' README.md  # Should include 9 data rows (excluding header/separator)
```

**Pass criteria**: 9 modules documented: hooks, speckit, mcp_servers, ci_workflows, docker, visualization, uv_project, sphinx_docs, vcs_hooks.

---

## SC-003: Zero D2 References

```bash
grep -inE 'd2|d2_gen|schema_gen|noodles|infra.console' README.md
```

**Pass criteria**: Zero matches.

---

## SC-004: Pipeline Stage Accuracy

```bash
# Verify 8 stages in correct order
grep -A1 'pipeline' README.md | grep -oP 'lint|typecheck|test|security|docs-api|docs-narrative|infra-sync|commit-message'
```

**Pass criteria**: All 8 stages present. First 5 marked "hard", last 3 marked "soft".

---

## SC-005: New User Walkthrough

Manual verification:

1. Read only the README (no spec documents)
2. Execute every code block in order from "Quickstart" through "Validation Checklist"
3. Confirm each command succeeds or the README explains expected output
4. Confirm no step requires knowledge from spec documents

**Pass criteria**: All code blocks execute without undocumented errors.

---

## SC-006: Repository Layout Accuracy

```bash
# Compare documented tree against actual structure
# Key directories that MUST appear in the tree:
for dir in vcs rules visualization brownfield pipeline modules cli templates; do
  grep -q "$dir/" README.md && echo "OK: $dir" || echo "MISSING: $dir"
done
```

**Pass criteria**: All 8 directories present. No phantom directories listed.

---

## SC-007: Spec Directory References

```bash
for spec in 001 002 003 004; do
  grep -q "specs/$spec" README.md && echo "OK: $spec" || echo "MISSING: $spec"
done
```

**Pass criteria**: All 4 spec directories referenced.

---

## SC-008: Optional Dependencies Marked

```bash
# Verify "Optional" appears for each optional tool
for tool in codeboarding git-cliff semantic-release gh glab mypy sphinx; do
  grep -i "$tool" README.md | grep -iq 'optional' && echo "OK: $tool" || echo "CHECK: $tool"
done
```

**Pass criteria**: All 7 optional tools appear in the prerequisites table with "Optional" in the Required? column.

---

## Additional Checks

### No Duplicate Sections (FR-017)

```bash
# Count occurrences of each h2 heading
grep '^## ' README.md | sort | uniq -c | sort -rn | head
```

**Pass criteria**: Every heading appears exactly once.

### Constitution Compliance

- **CLI-First**: All features documented via CLI commands ✓
- **Modularity**: Module catalog is a table, easy to extend ✓
- **Observability**: Pipeline stages and gate modes visible ✓

---

## Summary Checklist

| SC | Description | Method | Status |
|----|-------------|--------|--------|
| SC-001 | CLI commands complete | Automated diff | ☐ |
| SC-002 | Module catalog complete | Automated count | ☐ |
| SC-003 | Zero D2 references | Automated grep | ☐ |
| SC-004 | 8 pipeline stages correct | Automated grep | ☐ |
| SC-005 | New user walkthrough | Manual test | ☐ |
| SC-006 | Repo layout accurate | Automated check | ☐ |
| SC-007 | Spec dirs referenced | Automated check | ☐ |
| SC-008 | Optional deps marked | Automated grep | ☐ |
