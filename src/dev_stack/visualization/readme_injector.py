"""README injection and ledger management for visualization diagrams."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..brownfield import markers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Injection helpers
# ---------------------------------------------------------------------------


def inject_diagram(readme_path: Path, marker_id: str, mermaid_content: str) -> bool:
    """Inject a Mermaid diagram into *readme_path* inside managed markers.

    Creates the README file if it doesn't exist.  Returns *True* if the file
    was modified.
    """

    block = f"```mermaid\n{mermaid_content}\n```"
    try:
        return markers.write_managed_section(readme_path, marker_id, block)
    except PermissionError:
        logger.warning("Permission denied writing to %s — skipping", readme_path)
        return False


def remove_diagram(readme_path: Path, marker_id: str) -> bool:
    """Remove a managed Mermaid section from *readme_path*.

    Since ``markers.py`` has no dedicated removal function, this writes an
    empty section then strips the leftover empty marker pair.
    """

    if not readme_path.exists():
        return False

    start_marker, end_marker = markers._marker_pair(readme_path, marker_id)
    text = readme_path.read_text(encoding="utf-8")

    start_idx = text.find(start_marker)
    if start_idx == -1:
        return False

    end_idx = text.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1:
        return False

    # Remove the entire marker block (including any surrounding newlines)
    end_idx += len(end_marker)
    # Consume trailing newline if present
    if end_idx < len(text) and text[end_idx] == "\n":
        end_idx += 1

    new_text = text[:start_idx] + text[end_idx:]
    # Clean up double blank lines left behind
    while "\n\n\n" in new_text:
        new_text = new_text.replace("\n\n\n", "\n\n")

    if new_text == text:
        return False

    readme_path.write_text(new_text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Injection Ledger
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LedgerEntry:
    readme_path: str
    marker_id: str
    component_name: str | None = None


@dataclass(slots=True)
class InjectionLedger:
    version: int = 1
    generated_at: str = ""
    entries: list[LedgerEntry] = field(default_factory=list)

    # --- persistence -------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "InjectionLedger":
        """Load ledger from disk; returns an empty ledger if the file is missing."""

        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = [
                LedgerEntry(
                    readme_path=e.get("readme_path", ""),
                    marker_id=e.get("marker_id", ""),
                    component_name=e.get("component_name"),
                )
                for e in data.get("entries", [])
            ]
            return cls(
                version=data.get("version", 1),
                generated_at=data.get("generated_at", ""),
                entries=entries,
            )
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read injection ledger at %s", path)
            return cls()

    def save(self, path: Path) -> None:
        """Persist ledger to disk."""

        path.parent.mkdir(parents=True, exist_ok=True)
        self.generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": self.version,
            "generated_at": self.generated_at,
            "entries": [
                {
                    "readme_path": e.readme_path,
                    "marker_id": e.marker_id,
                    "component_name": e.component_name,
                }
                for e in self.entries
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # --- mutation -----------------------------------------------------------

    def add_entry(
        self,
        readme_path: str,
        marker_id: str,
        component_name: str | None = None,
    ) -> None:
        """Add an entry, replacing any existing entry for the same (readme, marker) pair."""

        self.entries = [
            e for e in self.entries if not (e.readme_path == readme_path and e.marker_id == marker_id)
        ]
        self.entries.append(LedgerEntry(readme_path, marker_id, component_name))

    def clear(self) -> None:
        self.entries.clear()


# ---------------------------------------------------------------------------
# High-level injection API
# ---------------------------------------------------------------------------


def inject_root_diagram(
    repo_root: Path,
    mermaid_content: str,
    ledger: InjectionLedger,
) -> bool:
    """Inject the top-level architecture diagram into ``repo_root/README.md``.

    Updates *ledger* in place.  Returns *True* if the README was modified.
    """

    readme = repo_root / "README.md"
    modified = inject_diagram(readme, "architecture", mermaid_content)
    ledger.add_entry("README.md", "architecture", component_name=None)
    return modified


def inject_component_diagrams(
    repo_root: Path,
    components: list,
    ledger: InjectionLedger,
) -> dict:
    """Inject sub-diagrams into per-folder README files.

    Parameters
    ----------
    repo_root:
        Repository root.
    components:
        List of ``ParsedComponent`` instances (from ``parse_components``).
    ledger:
        Injection ledger to update.

    Returns
    -------
    dict
        ``{"diagrams_injected": int, "readmes_modified": list[str]}``
    """

    diagrams_injected = 0
    readmes_modified: list[str] = []

    for comp in components:
        target_folder = getattr(comp, "target_folder", None)
        mermaid = getattr(comp, "mermaid", None)

        if not target_folder or not mermaid:
            if mermaid and not target_folder:
                logger.debug(
                    "Skipping component %r — no target folder computed", comp.name
                )
            continue

        readme_path = repo_root / target_folder / "README.md"
        rel_path = str(Path(target_folder) / "README.md")

        if inject_diagram(readme_path, "component-architecture", mermaid):
            readmes_modified.append(rel_path)

        diagrams_injected += 1
        ledger.add_entry(rel_path, "component-architecture", component_name=comp.name)

    return {"diagrams_injected": diagrams_injected, "readmes_modified": readmes_modified}
