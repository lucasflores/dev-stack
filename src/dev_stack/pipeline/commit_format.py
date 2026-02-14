"""Helpers for formatting and parsing commit trailers."""
from __future__ import annotations

from dataclasses import dataclass

TRAILER_ORDER = ("Spec-Ref", "Task-Ref", "Agent", "Pipeline", "Edited")


@dataclass(slots=True)
class TrailerData:
    """Structured trailer values appended to commit messages."""

    spec_ref: str | None = None
    task_ref: str | None = None
    agent: str | None = None
    pipeline: str | None = None
    edited: bool | None = None


def extract_trailers(message: str) -> tuple[str, dict[str, list[str]]]:
    """Split commit text into body and trailers."""

    lines = message.rstrip().splitlines()
    trailers: dict[str, list[str]] = {}
    idx = len(lines)
    while idx > 0:
        line = lines[idx - 1].strip()
        if not line:
            idx -= 1
            continue
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        key = key.strip()
        if not key or key not in TRAILER_ORDER:
            break
        value = value.strip()
        trailers.setdefault(key, []).insert(0, value)
        idx -= 1
    body = "\n".join(lines[:idx]).rstrip()
    return body, trailers


def format_trailers(data: TrailerData) -> str:
    """Render trailers in a deterministic order."""

    values = {
        "Spec-Ref": data.spec_ref,
        "Task-Ref": data.task_ref,
        "Agent": data.agent,
        "Pipeline": data.pipeline,
        "Edited": "true" if data.edited else ("false" if data.edited is not None else None),
    }
    lines = [f"{key}: {value}" for key in TRAILER_ORDER if (value := values.get(key))]
    return "\n".join(lines)


def upsert_trailers(message: str, data: TrailerData) -> str:
    """Ensure the commit message ends with the desired trailers."""

    body, trailers = extract_trailers(message)
    rendered = format_trailers(
        TrailerData(
            spec_ref=data.spec_ref or _first(trailers.get("Spec-Ref")),
            task_ref=data.task_ref or _first(trailers.get("Task-Ref")),
            agent=data.agent or _first(trailers.get("Agent")),
            pipeline=data.pipeline or _first(trailers.get("Pipeline")),
            edited=data.edited if data.edited is not None else _parse_bool(_first(trailers.get("Edited"))),
        )
    )
    if rendered:
        return f"{body}\n\n{rendered}\n"
    return f"{body}\n"


def _first(values: list[str] | None) -> str | None:
    if values:
        return values[0]
    return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"true", "yes", "1"}:
        return True
    if lowered in {"false", "no", "0"}:
        return False
    return None
