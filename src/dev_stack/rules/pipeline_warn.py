"""PipelineFailureWarningRule (UC4) — warns on pipeline stage failures.

Parses the ``Pipeline:`` trailer and emits non-blocking warnings for any
stage with a ``=fail`` value.
"""
from __future__ import annotations

from gitlint.rules import CommitRule, RuleViolation


def _parse_pipeline_trailer(value: str) -> dict[str, str]:
    """Parse comma-separated ``key=value`` pairs from a Pipeline trailer value.

    Example input: ``lint=pass,typecheck=fail,test=pass``
    Returns: ``{"lint": "pass", "typecheck": "fail", "test": "pass"}``
    """
    results: dict[str, str] = {}
    for part in value.split(","):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            results[k.strip()] = v.strip()
    return results


def _parse_trailers(body_lines: list[str]) -> dict[str, str]:
    """Parse git-trailer-style key: value pairs from body lines."""
    trailers: dict[str, str] = {}
    for line in reversed(body_lines):
        stripped = line.strip()
        if not stripped:
            break
        if ": " in stripped:
            key, _, value = stripped.partition(": ")
            trailers[key.strip()] = value.strip()
        else:
            break
    return trailers


class PipelineFailureWarningRule(CommitRule):
    """Emit non-blocking warnings for pipeline stage failures (UC4).

    Parses the ``Pipeline:`` trailer value (comma-separated ``key=value``
    pairs) and emits a warning-level violation for each ``=fail`` entry.
    """

    name = "dev-stack-pipeline-warning"
    id = "UC4"

    def validate(self, commit):  # type: ignore[override]
        body_lines = commit.message.body if commit.message.body else []
        trailers = _parse_trailers(body_lines)

        pipeline_value = trailers.get("Pipeline")
        if not pipeline_value:
            return []

        stages = _parse_pipeline_trailer(pipeline_value)
        violations: list[RuleViolation] = []
        for stage, status in stages.items():
            if status == "fail":
                violations.append(
                    RuleViolation(
                        self.id,
                        f"Pipeline stage '{stage}' failed. "
                        f"Review the failure before proceeding.",
                        line_nr=1,
                    )
                )
        return violations
