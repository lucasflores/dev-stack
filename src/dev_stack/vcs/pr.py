"""PR description generation — aggregates commits and renders Markdown.

Provides :class:`PRDescription` and :func:`render_pr_description`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from dev_stack.vcs.commit_parser import CommitSummary

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# All recognised pipeline stages
_PIPELINE_STAGES = (
    "lint", "typecheck", "test", "security",
    "docs-api", "docs-narrative", "infra-sync", "commit-message",
)


@dataclass(slots=True)
class PRDescription:
    """Aggregated PR description built from branch commits."""

    title: str
    summary: str
    spec_refs: list[str] = field(default_factory=list)
    task_refs: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    pipeline_status: dict[str, str] = field(default_factory=dict)
    edited_count: int = 0
    total_commits: int = 0
    ai_commits: int = 0
    commits: list[CommitSummary] = field(default_factory=list)


def build_pr_description(
    commits: list[CommitSummary],
    *,
    branch: str = "",
    base: str = "main",
) -> PRDescription:
    """Aggregate *commits* into a :class:`PRDescription`.

    Args:
        commits: Parsed commits (newest first).
        branch: Current branch name (used for title fallback).
        base: Base branch.

    Returns:
        Populated :class:`PRDescription`.
    """
    spec_refs: set[str] = set()
    task_refs: set[str] = set()
    agents: set[str] = set()
    pipeline_agg: dict[str, list[str]] = {}
    edited_count = 0
    ai_count = 0

    for c in commits:
        if c.is_ai_authored:
            ai_count += 1
        if c.is_human_edited:
            edited_count += 1

        # Aggregate trailers
        sr = c.trailers.get("Spec-Ref")
        if sr:
            spec_refs.add(sr)
        tr = c.trailers.get("Task-Ref")
        if tr:
            task_refs.add(tr)
        agent = c.trailers.get("Agent")
        if agent:
            agents.add(agent)

        # Aggregate pipeline
        pipeline_raw = c.trailers.get("Pipeline", "")
        if pipeline_raw:
            for entry in pipeline_raw.split(","):
                entry = entry.strip()
                if "=" in entry:
                    stage, status = entry.split("=", 1)
                    pipeline_agg.setdefault(stage.strip(), []).append(status.strip())

    # Compute worst-case status per stage
    pipeline_status: dict[str, str] = {}
    for stage in _PIPELINE_STAGES:
        statuses = pipeline_agg.get(stage, [])
        if not statuses:
            pipeline_status[stage] = "n/a"
        elif "fail" in statuses:
            pipeline_status[stage] = "fail"
        elif "warn" in statuses:
            pipeline_status[stage] = "warn"
        elif "skip" in statuses:
            pipeline_status[stage] = "skip"
        else:
            pipeline_status[stage] = "pass"

    # Build title
    if commits:
        title = commits[0].subject
    elif branch:
        title = branch
    else:
        title = "Pull Request"

    # Build summary — group by type
    type_counts: dict[str, int] = {}
    for c in commits:
        type_counts[c.type] = type_counts.get(c.type, 0) + 1
    summary_parts = []
    for t, count in sorted(type_counts.items()):
        summary_parts.append(f"{count} {t}" + ("s" if count > 1 else ""))
    summary = f"Changes: {', '.join(summary_parts)}" if summary_parts else "No changes"

    return PRDescription(
        title=title,
        summary=summary,
        spec_refs=sorted(spec_refs),
        task_refs=sorted(task_refs),
        agents=sorted(agents),
        pipeline_status=pipeline_status,
        edited_count=edited_count,
        total_commits=len(commits),
        ai_commits=ai_count,
        commits=commits,
    )


def render_pr_markdown(desc: PRDescription) -> str:
    """Render :class:`PRDescription` as Markdown using the PR template.

    Uses simple ``{{ var }}`` replacement rather than requiring Jinja2
    as a dependency.

    Returns:
        Rendered Markdown string.
    """
    template_path = TEMPLATE_DIR / "pr-template.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        # Fallback minimal template
        template = "## Summary\n\n{{ summary }}\n"

    # Compute derived values
    ai_pct = (
        round(desc.ai_commits / desc.total_commits * 100)
        if desc.total_commits > 0
        else 0
    )
    agents_list = ", ".join(desc.agents) if desc.agents else "none"

    # Simple template rendering via str.replace won't handle loops, so
    # we do manual rendering.
    lines: list[str] = []
    lines.append("## Summary")
    lines.append("")
    lines.append(desc.summary)
    lines.append("")
    lines.append("## Spec References")
    lines.append("")
    if desc.spec_refs:
        for ref in desc.spec_refs:
            lines.append(f"- {ref}")
    else:
        lines.append("_No spec references found._")
    lines.append("")
    lines.append("## Task References")
    lines.append("")
    if desc.task_refs:
        for ref in desc.task_refs:
            lines.append(f"- {ref}")
    else:
        lines.append("_No task references found._")
    lines.append("")
    lines.append("## AI Provenance")
    lines.append("")
    lines.append(f"- **Total commits**: {desc.total_commits}")
    lines.append(f"- **AI-authored**: {desc.ai_commits} ({ai_pct}%)")
    lines.append(f"- **Human-edited**: {desc.edited_count}")
    lines.append(f"- **Agents used**: {agents_list}")
    lines.append("")
    lines.append("## Pipeline Status")
    lines.append("")
    lines.append("| Stage | Status |")
    lines.append("|-------|--------|")
    for stage, status in desc.pipeline_status.items():
        lines.append(f"| {stage} | {status} |")
    lines.append("")
    lines.append("## Commits")
    lines.append("")
    for c in desc.commits:
        suffix = ""
        if c.is_ai_authored:
            suffix += " 🤖"
        if c.is_human_edited:
            suffix += " ✏️"
        lines.append(f"- [`{c.short_sha}`] {c.subject}{suffix}")
    lines.append("")

    return "\n".join(lines)
