"""Parse CodeBoarding output and extract Mermaid diagrams."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import CodeBoardingError

logger = logging.getLogger(__name__)

# Regex to capture the first fenced mermaid code block.
_MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


# ---------------------------------------------------------------------------
# Dataclasses mirroring data-model.md entities
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class KeyEntity:
    qualified_name: str
    reference_file: str
    reference_start_line: int | None = None
    reference_end_line: int | None = None


@dataclass(slots=True)
class ComponentRelation:
    relation: str
    src_name: str
    dst_name: str
    src_id: str
    dst_id: str


@dataclass(slots=True)
class Component:
    name: str
    description: str
    key_entities: list[KeyEntity]
    assigned_files: list[str]
    component_id: str
    can_expand: bool
    components: list["Component"] = field(default_factory=list)
    components_relations: list[ComponentRelation] = field(default_factory=list)


@dataclass(slots=True)
class AnalysisMetadata:
    generated_at: str
    repo_name: str
    depth_level: int
    file_coverage_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnalysisIndex:
    metadata: AnalysisMetadata
    description: str
    components: list[Component]
    components_relations: list[ComponentRelation]


@dataclass(slots=True)
class ParsedComponent:
    """A component with its extracted Mermaid diagram and folder mapping."""

    name: str
    component_id: str
    mermaid: str | None
    assigned_files: list[str]
    can_expand: bool
    sub_components: list["ParsedComponent"]
    target_folder: str | None = None


# ---------------------------------------------------------------------------
# Folder mapping
# ---------------------------------------------------------------------------


def compute_target_folder(assigned_files: list[str]) -> str | None:
    """Return the longest common directory prefix of *assigned_files*.

    Returns *None* if the list is empty or all files sit at the repo root.

    Examples
    --------
    >>> compute_target_folder(["agents/agent.py", "agents/constants.py"])
    'agents'
    >>> compute_target_folder(["main.py"])  # root-level
    """

    if not assigned_files:
        return None

    from pathlib import PurePosixPath

    dirs = [str(PurePosixPath(f).parent) for f in assigned_files]
    # Find the common prefix among directory parts
    if not dirs:
        return None

    # Split each dir into parts
    split = [d.split("/") for d in dirs]
    prefix_parts: list[str] = []
    for parts in zip(*split):
        if len(set(parts)) == 1 and parts[0] != ".":
            prefix_parts.append(parts[0])
        else:
            break

    if not prefix_parts:
        return None

    return "/".join(prefix_parts)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_key_entity(raw: dict[str, Any]) -> KeyEntity:
    return KeyEntity(
        qualified_name=raw.get("qualified_name", ""),
        reference_file=raw.get("reference_file", ""),
        reference_start_line=raw.get("reference_start_line"),
        reference_end_line=raw.get("reference_end_line"),
    )


def _parse_relation(raw: dict[str, Any]) -> ComponentRelation:
    return ComponentRelation(
        relation=raw.get("relation", ""),
        src_name=raw.get("src_name", ""),
        dst_name=raw.get("dst_name", ""),
        src_id=raw.get("src_id", ""),
        dst_id=raw.get("dst_id", ""),
    )


def _parse_component(raw: dict[str, Any]) -> Component:
    return Component(
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        key_entities=[_parse_key_entity(e) for e in raw.get("key_entities", [])],
        assigned_files=raw.get("assigned_files", []),
        component_id=raw.get("component_id", ""),
        can_expand=raw.get("can_expand", False),
        components=[_parse_component(c) for c in raw.get("components", [])],
        components_relations=[_parse_relation(r) for r in raw.get("components_relations", [])],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_analysis_index(path: Path) -> AnalysisIndex:
    """Load and parse ``.codeboarding/analysis.json``.

    Raises
    ------
    CodeBoardingError
        If the file is missing or contains malformed JSON.
    """

    if not path.exists():
        raise CodeBoardingError(f"analysis.json not found at {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CodeBoardingError(f"Failed to parse {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise CodeBoardingError(f"Expected JSON object in {path}")

    raw_meta = data.get("metadata", {})
    metadata = AnalysisMetadata(
        generated_at=raw_meta.get("generated_at", ""),
        repo_name=raw_meta.get("repo_name", ""),
        depth_level=raw_meta.get("depth_level", 1),
        file_coverage_summary=raw_meta.get("file_coverage_summary", {}),
    )

    components = [_parse_component(c) for c in data.get("components", [])]
    relations = [_parse_relation(r) for r in data.get("components_relations", [])]

    return AnalysisIndex(
        metadata=metadata,
        description=data.get("description", ""),
        components=components,
        components_relations=relations,
    )


def extract_mermaid(md_path: Path) -> str | None:
    """Extract the first fenced Mermaid code block from a markdown file.

    Returns *None* if no mermaid block is found or the file doesn't exist.
    """

    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    match = _MERMAID_RE.search(text)
    return match.group(1).strip() if match else None


def derive_markdown_filename(component_name: str) -> str:
    """Derive the CodeBoarding markdown filename from a component name.

    Non-alphanumeric characters are replaced with underscores.

    Example: ``"LLM Agent Core"`` → ``"LLM_Agent_Core.md"``
    """

    sanitised = re.sub(r"[^A-Za-z0-9]+", "_", component_name).strip("_")
    return f"{sanitised}.md"


def parse_components(codeboarding_dir: Path) -> list[ParsedComponent]:
    """Parse the analysis index and extract Mermaid diagrams for each component.

    Parameters
    ----------
    codeboarding_dir:
        Path to the ``.codeboarding/`` directory.

    Returns
    -------
    list[ParsedComponent]
        One entry per top-level component, with nested sub-components.
    """

    index_path = codeboarding_dir / "analysis.json"
    index = parse_analysis_index(index_path)

    def _build(component: Component) -> ParsedComponent:
        md_name = derive_markdown_filename(component.name)
        md_path = codeboarding_dir / md_name
        mermaid = extract_mermaid(md_path)
        if mermaid is None and md_path.suffix == ".md":
            logger.warning("Missing or empty Mermaid in %s – skipping component %r", md_path, component.name)

        sub_components = [_build(sc) for sc in component.components]
        return ParsedComponent(
            name=component.name,
            component_id=component.component_id,
            mermaid=mermaid,
            assigned_files=component.assigned_files,
            can_expand=component.can_expand,
            sub_components=sub_components,
            target_folder=compute_target_folder(component.assigned_files),
        )

    return [_build(c) for c in index.components]
