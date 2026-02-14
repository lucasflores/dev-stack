"""D2 generator utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "overview.d2"

NODE_CLASS = {
    "entry_point": "entry_node",
    "feature_block": "feature_node",
    "end": "terminal_node",
}

STATUS_BADGE = {
    "added": "[added]",
    "updated": "[updated]",
    "unchanged": "",
}

DEFAULT_STATUS = "unchanged"

STATUS_STYLE = {
    "added": {
        "style.stroke": "#1fffe1",
        "style.fill": "#031c2a",
    },
    "updated": {
        "style.stroke": "#f59e0b",
        "style.fill": "#120f03",
    },
    "unchanged": {},
}

HIGHLIGHT_STYLE = {
    "style.shadow-color": "#13f2ff",
    "style.shadow-blur": 60,
    "style.stroke-width": 3.2,
}

FLOW_CLASS = {
    "added": "flow_link",
    "updated": "flow_link",
    "unchanged": "flow_link_secondary",
}

FLOW_STYLE = {
    "added": {
        "style.stroke": "#13d6ff",
    },
    "updated": {
        "style.stroke": "#facc15",
    },
    "unchanged": {},
}


class D2Generator:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    def render_overview(self, schema: dict[str, Any], *, highlight_paths: Iterable[str] | None = None) -> str:
        highlight = {str(path) for path in (highlight_paths or [])}
        nodes = schema.get("nodes", [])
        flows = schema.get("flows", [])
        id_map = self._build_id_map(nodes)
        prepared_nodes = [self._prepare_node(node, highlight, id_map, idx) for idx, node in enumerate(nodes)]
        prepared_flows = [self._prepare_flow(flow, id_map) for flow in flows]

        base = TEMPLATE_PATH.read_text(encoding="utf-8")
        lines: list[str] = [base]
        for block in prepared_nodes:
            lines.append(block)
        for block in prepared_flows:
            if block:
                lines.append(block)
        lines.append("}")
        return "\n".join(lines)

    def render_json(
        self,
        schema: dict[str, Any],
        *,
        output_path: Path,
        highlight_paths: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_schema(schema, highlight_paths)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        return normalized

    # ------------------------------------------------------------------
    def _prepare_node(
        self,
        node: dict[str, Any],
        highlight: set[str],
        id_map: dict[str, str],
        index: int,
    ) -> str:
        node_id = self._lookup_node_id(node, id_map, index)
        status = self._derive_status(node, highlight)
        label = node.get("name") or node.get("id") or f"Node {index + 1}"
        badge = STATUS_BADGE.get(status, "")
        description = node.get("description", "")
        tooltip = self._format_tooltip(node.get("files", []))
        note = self._format_note(node.get("files", []))
        node_class = self._node_class(node)
        highlighted = self._is_highlighted(node, highlight)

        block_lines = [f"  {node_id} {{", f"    label: \"{self._escape(self._with_badge(label, badge))}\""]
        block_lines.append(f"    class: {node_class}")
        if description:
            block_lines.append(f"    description: \"{self._escape(description)}\"")
        if tooltip:
            block_lines.append(f"    tooltip: \"{self._escape(tooltip)}\"")
        if note:
            block_lines.append(f"    note: \"{self._escape(note)}\"")
        self._append_styles(block_lines, STATUS_STYLE.get(status, {}))
        if highlighted:
            self._append_styles(block_lines, HIGHLIGHT_STYLE)
        block_lines.append("  }")
        return "\n".join(block_lines)

    def _prepare_flow(self, flow: dict[str, Any], id_map: dict[str, str]) -> str | None:
        start = self._lookup_flow_endpoint(flow.get("from"), id_map)
        end = self._lookup_flow_endpoint(flow.get("to"), id_map)
        if not start or not end:
            return None
        description = flow.get("description", "")
        status = flow.get("status", DEFAULT_STATUS)
        flow_class = FLOW_CLASS.get(status, "flow_link")
        block_lines = [f"  {start} -> {end} {{", f"    class: {flow_class}"]
        if description:
            block_lines.append(f"    label: \"{self._escape(description)}\"")
        self._append_styles(block_lines, FLOW_STYLE.get(status, {}))
        block_lines.append("  }")
        return "\n".join(block_lines)

    def _normalize_schema(self, schema: dict[str, Any], highlight_paths: Iterable[str] | None) -> dict[str, Any]:
        highlight = {str(path) for path in (highlight_paths or [])}
        nodes = {}
        for idx, node in enumerate(schema.get("nodes", [])):
            key = self._node_key(node, idx)
            nodes[key] = {
                "id": node.get("id"),
                "type": node.get("type"),
                "name": node.get("name"),
                "description": node.get("description"),
                "files": node.get("files", []),
                "status": self._derive_status(node, highlight),
            }
        flows = []
        for flow in schema.get("flows", []):
            flows.append(
                {
                    "from": flow.get("from"),
                    "to": flow.get("to"),
                    "description": flow.get("description", ""),
                    "status": flow.get("status", DEFAULT_STATUS),
                }
            )
        return {"nodes": nodes, "flows": flows}

    # ------------------------------------------------------------------
    def _lookup_node_id(self, node: dict[str, Any], id_map: dict[str, str], index: int) -> str:
        raw_id = node.get("id") or node.get("name") or f"node_{index}"
        sanitized = id_map.get(raw_id)
        if sanitized:
            return sanitized
        sanitized = self._sanitize_id(raw_id)
        id_map[raw_id] = sanitized
        return sanitized

    def _lookup_flow_endpoint(self, value: Any, id_map: dict[str, str]) -> str | None:
        if value is None:
            return None
        if value in id_map:
            return id_map[value]
        sanitized = self._sanitize_id(str(value))
        id_map[value] = sanitized
        return sanitized

    def _build_id_map(self, nodes: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for idx, node in enumerate(nodes):
            raw_id = node.get("id") or node.get("name") or f"node_{idx}"
            sanitized = self._sanitize_id(raw_id)
            while sanitized in mapping.values():
                sanitized = f"{sanitized}_{idx}"
            mapping[raw_id] = sanitized
            mapping[sanitized] = sanitized
        return mapping

    def _derive_status(self, node: dict[str, Any], highlight: set[str]) -> str:
        files = node.get("files", [])
        status = node.get("status") or DEFAULT_STATUS
        for ref in files:
            file_path = str(ref.get("file")) if ref.get("file") is not None else None
            if file_path and file_path in highlight:
                if status == DEFAULT_STATUS:
                    return "updated"
                return status
        return status

    def _node_key(self, node: dict[str, Any], index: int) -> str:
        files = node.get("files", [])
        if files:
            file_ref = files[0]
            if file_ref.get("file"):
                return str(file_ref["file"])
        return node.get("id") or node.get("name") or f"node_{index}"

    def _node_class(self, node: dict[str, Any]) -> str:
        node_type = node.get("type")
        return NODE_CLASS.get(node_type, "feature_node")

    def _is_highlighted(self, node: dict[str, Any], highlight: set[str]) -> bool:
        files = node.get("files", [])
        for ref in files:
            file_path = ref.get("file")
            if file_path and str(file_path) in highlight:
                return True
        return False

    def _append_styles(self, block_lines: list[str], styles: dict[str, Any]) -> None:
        for key, value in styles.items():
            if isinstance(value, (int, float)):
                block_lines.append(f"    {key}: {value}")
            else:
                block_lines.append(f"    {key}: \"{self._escape(str(value))}\"")

    def _format_tooltip(self, files: list[dict[str, Any]]) -> str:
        tooltip_parts: list[str] = []
        for ref in files:
            file_path = ref.get("file")
            lines = ref.get("lines") or []
            if file_path:
                if len(lines) == 2:
                    tooltip_parts.append(f"{file_path}:{lines[0]}-{lines[1]}")
                else:
                    tooltip_parts.append(str(file_path))
        return "\n".join(tooltip_parts)

    def _format_note(self, files: list[dict[str, Any]]) -> str:
        if not files:
            return ""
        return "\n".join(str(ref.get("file")) for ref in files if ref.get("file"))

    def _with_badge(self, label: str, badge: str) -> str:
        return f"{label} {badge}".strip()

    def _sanitize_id(self, value: str) -> str:
        if not value:
            return "node"
        sanitized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
        if not sanitized:
            sanitized = "node"
        if not sanitized[0].isalpha():
            sanitized = f"n_{sanitized}"
        return sanitized

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
