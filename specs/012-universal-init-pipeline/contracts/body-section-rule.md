# Contract: Body Section Validation Rule

**Module**: `src/dev_stack/rules/body_sections.py`  
**Class**: `BodySectionRule` (gitlint rule ID: `UC5`)

## Purpose

Validate that agent-generated commits contain all four required body sections: Intent, Reasoning, Scope, and Narrative (FR-003, FR-004, FR-011).

## Rule Definition

```python
class BodySectionRule(CommitRule):
    """Require body sections on agent-generated commits (UC5)."""
    
    name = "dev-stack-body-sections"
    id = "UC5"
    
    REQUIRED_SECTIONS: tuple[str, ...] = (
        "## Intent",
        "## Reasoning",
        "## Scope",
        "## Narrative",
    )
```

## Behavior

### Detection of Agent Commits

An "agent commit" is identified by the presence of an `Agent:` trailer in the commit body (consistent with existing UC2 rule logic).

```python
trailers = _parse_trailers(body_lines)
if "Agent" not in trailers:
    return []  # Human commit — no enforcement (FR-004)
```

### Section Validation

For agent commits, scan the body for markdown headings matching each required section:

```python
body_text = "\n".join(body_lines)
missing = [
    section for section in REQUIRED_SECTIONS
    if section not in body_text
]
```

### Error Reporting (FR-011)

When sections are missing, return a `RuleViolation` listing all absent sections:

```
Error [UC5]: Agent commit missing required body sections: ## Intent, ## Scope
Agent commits must include: ## Intent, ## Reasoning, ## Scope, ## Narrative
```

## Test Cases

| Scenario | Input | Expected |
|----------|-------|----------|
| Agent commit, all sections | Agent: trailer + 4 sections | PASS (no violations) |
| Agent commit, no sections | Agent: trailer + empty body | FAIL: lists all 4 missing |
| Agent commit, partial | Agent: trailer + Intent + Scope | FAIL: lists Reasoning, Narrative |
| Human commit, no sections | No Agent: trailer, no sections | PASS (not enforced) |
| Human commit, with sections | No Agent: trailer, has sections | PASS |
| Agent commit, sections as h3 | Agent: trailer + ### Intent | FAIL (must be ## not ###) |

## Integration

- Loaded automatically by gitlint via `config.extra_path = rules_path` in `run_commit_msg_hook()`
- No changes needed to `hooks_runner.py` — gitlint discovers rules in the `dev_stack.rules` package
- Rule UC5 runs alongside UC1 (conventional), UC2 (trailers), UC3 (paths), UC4 (pipeline warnings)

## Invariants

- Human commits NEVER trigger body section validation (FR-004, SC-003)
- All 4 sections MUST be present for agent commit to pass (FR-003, SC-002)
- Error message MUST list which specific sections are missing (FR-011)
