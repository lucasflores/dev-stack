"""Schema generation via AgentBridge with cached fallback."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..errors import AgentUnavailableError
from ..pipeline.agent_bridge import AgentBridge

OVERVIEW_PROMPT = """You are analyzing a codebase to generate a structured architecture diagram.\n\nGiven these source files:\n{SOURCE}\n\nIdentify ONLY user-facing, interactive entry points (APIs, CLI commands, UI routes) and the feature blocks they connect to.\n\nReturn JSON only with top-level keys: nodes, flows.\n\nnodes: array of {id, type, name, description, files}\n  - type: "entry_point" | "feature_block" | "end"\n  - files: array of {file, lines: [start, end]}\n\nflows: array of {from, to, description}\n\nRules:\n- Entry points: real user interactions only\n- Feature blocks: coherent functional units\n- Every node must participate in at least one flow\n- No orphan nodes\n  """


@dataclass(slots=True)
class SchemaResult:
    content: dict
    raw_text: str


class SchemaGenerationError(RuntimeError):
    def __init__(self, message: str, *, cached_schema: dict | None = None) -> None:
        super().__init__(message)
        self.cached_schema = cached_schema


class SchemaGenerator:
    def __init__(
        self,
        repo_root: Path,
        agent_bridge: AgentBridge | None = None,
        *,
        cache_path: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.agent_bridge = agent_bridge or AgentBridge(repo_root)
        self.cache_path = cache_path or (self.repo_root / ".dev-stack" / "viz" / "overview.json")

    def load_cached_schema(self) -> dict | None:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:  # pragma: no cover - defensive
            return None

    def generate_overview(self, source_snapshot: Path) -> SchemaResult:
        prompt = OVERVIEW_PROMPT.replace("{SOURCE}", source_snapshot.read_text(encoding="utf-8"))
        cached = self.load_cached_schema()
        try:
            response = self.agent_bridge.invoke(prompt, json_output=True)
        except AgentUnavailableError as exc:
            raise SchemaGenerationError(str(exc), cached_schema=cached) from exc
        if not response.success or not response.json_data:
            message = response.error or "Agent failed to return overview schema"
            raise SchemaGenerationError(message, cached_schema=cached)
        result = SchemaResult(content=response.json_data, raw_text=response.content)
        self._persist_cache(result.content)
        return result

    def _persist_cache(self, schema: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
