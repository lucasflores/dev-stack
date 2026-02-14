"""Subprocess-based bridge to coding agent CLIs."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from ..config import AgentInfo, detect_agent
from ..errors import AgentUnavailableError
from ..manifest import StackManifest

Executor = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class AgentResponse:
    """Structured response from an agent invocation."""

    success: bool
    content: str
    json_data: dict | list | None
    agent_cli: str
    duration_ms: int
    error: str | None = None


class AgentBridge:
    """Bridge that detects and invokes coding agent CLIs."""

    AGENT_PRIORITY = ("claude", "copilot", "cursor")

    def __init__(
        self,
        repo_root: Path,
        manifest: StackManifest | None = None,
        *,
        _executor: Executor | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.manifest = manifest
        self._executor: Executor = _executor or subprocess.run
        self._agent_info: AgentInfo | None = None

    # ------------------------------------------------------------------
    # Detection
    def detect(self) -> str:
        """Detect and cache the available agent CLI."""

        self._agent_info = detect_agent(self.manifest)
        return self._agent_info.cli

    def is_available(self) -> bool:
        info = self._agent_info or detect_agent(self.manifest)
        return bool(info.cli != "none" and (info.path or info.cli))

    # ------------------------------------------------------------------
    # Invocation
    def invoke(
        self,
        prompt: str,
        *,
        json_output: bool = False,
        context_files: Sequence[Path] | None = None,
        timeout_seconds: int = 120,
        system_prompt: str | None = None,
    ) -> AgentResponse:
        info = self._agent_info or detect_agent(self.manifest)
        self._agent_info = info
        if info.cli == "none":
            raise AgentUnavailableError("AgentBridge")

        rendered_prompt = self._render_prompt(prompt, context_files)
        if json_output and info.cli != "claude":
            rendered_prompt = (
                "Return ONLY JSON with no surrounding text. If you cannot, return an empty object.\n"
                + rendered_prompt
            )
        if system_prompt and info.cli != "claude":
            rendered_prompt = f"System instruction: {system_prompt}\n\n{rendered_prompt}"

        cmd, input_text, env = self._build_command(
            info, rendered_prompt, json_output, system_prompt
        )
        start = time.perf_counter()
        try:
            completed = self._executor(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            duration = int((time.perf_counter() - start) * 1000)
            return AgentResponse(
                success=False,
                content="",
                json_data=None,
                agent_cli=info.cli,
                duration_ms=duration,
                error=f"Timeout after {timeout_seconds}s",
            )

        duration = int((time.perf_counter() - start) * 1000)
        success = completed.returncode == 0
        content = completed.stdout.strip()
        error_msg = None if success else (completed.stderr.strip() or "Agent invocation failed")
        parsed_json = self._extract_json(content) if success and json_output else None
        return AgentResponse(
            success=success,
            content=content,
            json_data=parsed_json,
            agent_cli=info.cli,
            duration_ms=duration,
            error=error_msg,
        )

    # ------------------------------------------------------------------
    # Helpers
    def _render_prompt(self, prompt: str, context_files: Sequence[Path] | None) -> str:
        if not context_files:
            return prompt
        context_sections: list[str] = []
        for file_path in context_files:
            try:
                text = Path(file_path).read_text(encoding="utf-8")
            except FileNotFoundError:
                continue
            relative = os.path.relpath(file_path, self.repo_root)
            context_sections.append(f"\n# File: {relative}\n{text}")
        if not context_sections:
            return prompt
        return f"{prompt}\n\nContext files:{''.join(context_sections)}"

    def _build_command(
        self,
        info: AgentInfo,
        prompt: str,
        json_output: bool,
        system_prompt: str | None,
    ) -> tuple[list[str], str | None, dict[str, str] | None]:
        agent_cli = info.path or info.cli
        if info.cli == "claude":
            cmd = [agent_cli, "--print", "--max-turns", "1"]
            cmd.extend(["--output-format", "json" if json_output else "text"])
            if system_prompt:
                cmd.extend(["--system-prompt", system_prompt])
            return cmd, prompt, None
        if info.cli == "copilot":
            env = os.environ.copy()
            env.setdefault("COPILOT_ALLOW_ALL", "true")
            env.setdefault("NO_COLOR", os.environ.get("NO_COLOR", "1"))
            cmd = [agent_cli, "copilot", "--", "-p", prompt, "--allow-all", "--no-auto-update"]
            return cmd, None, env
        if info.cli == "cursor":
            cmd = [agent_cli, "--prompt", "-"]
            return cmd, prompt, None
        raise AgentUnavailableError("AgentBridge")

    @staticmethod
    def _extract_json(content: str) -> dict | list | None:
        data = content.strip()
        if not data:
            return None
        decoder = json.JSONDecoder()
        for opener in ("{", "["):
            try:
                start = data.index(opener)
            except ValueError:
                continue
            try:
                parsed, _ = decoder.raw_decode(data[start:])
                return parsed
            except json.JSONDecodeError:
                continue
        return None
