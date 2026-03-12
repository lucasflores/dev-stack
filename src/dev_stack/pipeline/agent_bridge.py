"""Subprocess-based bridge to coding agent CLIs."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from ..config import AgentInfo, detect_agent
from ..errors import AgentUnavailableError
from ..manifest import StackManifest

Executor = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class CommandSpec:
    cmd: list[str]
    input_text: str | None
    env: dict[str, str] | None
    cleanup: Callable[[], None] = lambda: None


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
        self._debug_enabled = os.environ.get("DEV_STACK_DEBUG", "").lower() in {"1", "true", "yes"}
        self._debug_file = self.repo_root / ".dev-stack" / "logs" / "agent_bridge.log"

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
        sandbox: bool = False,
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

        spec = self._build_command(info, rendered_prompt, json_output, system_prompt, sandbox=sandbox)
        self._log_debug(
            "agent_bridge.invoke.start",
            {
                "agent": info.cli,
                "cmd": spec.cmd,
                "json_output": json_output,
                "system_prompt": bool(system_prompt),
                "context_files": [str(p) for p in (context_files or [])],
                "prompt_preview": rendered_prompt[:2000],
            },
        )
        start = time.perf_counter()
        try:
            completed = self._executor(
                spec.cmd,
                input=spec.input_text,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                env=spec.env,
            )
        except subprocess.TimeoutExpired:
            duration = int((time.perf_counter() - start) * 1000)
            self._log_debug(
                "agent_bridge.invoke.timeout",
                {
                    "agent": info.cli,
                    "timeout_seconds": timeout_seconds,
                    "duration_ms": duration,
                },
            )
            return AgentResponse(
                success=False,
                content="",
                json_data=None,
                agent_cli=info.cli,
                duration_ms=duration,
                error=f"Timeout after {timeout_seconds}s",
            )
        finally:
            spec.cleanup()

        duration = int((time.perf_counter() - start) * 1000)
        success = completed.returncode == 0
        content = completed.stdout.strip()
        error_msg = None if success else (completed.stderr.strip() or "Agent invocation failed")
        self._log_debug(
            "agent_bridge.invoke.result",
            {
                "agent": info.cli,
                "returncode": completed.returncode,
                "duration_ms": duration,
                "stdout_preview": completed.stdout[:2000],
                "stderr_preview": completed.stderr[:2000],
            },
        )
        parsed_json = None
        if success and json_output:
            parsed_json = self._extract_json(content) or self._extract_json_from_file_reference(content)
            if parsed_json is None:
                self._log_debug(
                    "agent_bridge.invoke.json_parse_failed",
                    {
                        "agent": info.cli,
                        "stdout_preview": content[:2000],
                    },
                )
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
        *,
        sandbox: bool = False,
    ) -> CommandSpec:
        agent_cli = info.path or info.cli
        if info.cli == "claude":
            cmd = [agent_cli, "--print", "--max-turns", "1"]
            cmd.extend(["--output-format", "json" if json_output else "text"])
            if system_prompt:
                cmd.extend(["--system-prompt", system_prompt])
            if sandbox:
                cmd.extend(["--disallowedTools", "Edit,Write,Bash"])
            return CommandSpec(cmd=cmd, input_text=prompt, env=None)
        if info.cli == "copilot":
            env = os.environ.copy()
            tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
            try:
                tmp.write(prompt)
            finally:
                tmp.flush()
                tmp.close()

            def _cleanup() -> None:
                try:
                    os.unlink(tmp.name)
                except FileNotFoundError:
                    pass

            cmd = [
                agent_cli,
                "copilot",
                "--",
                "-p",
                f"@{tmp.name}",
                "--no-auto-update",
            ]
            if sandbox:
                cmd.extend([
                    "--deny-tool='write'",
                    "--allow-tool='read_file'",
                    "--allow-tool='grep_search'",
                    "--allow-tool='file_search'",
                    "--allow-tool='semantic_search'",
                    "--allow-tool='list_dir'",
                ])
            else:
                env.setdefault("COPILOT_ALLOW_ALL", "true")
                cmd.append("--allow-all")
            env.setdefault("NO_COLOR", os.environ.get("NO_COLOR", "1"))
            return CommandSpec(cmd=cmd, input_text=None, env=env, cleanup=_cleanup)
        if info.cli == "cursor":
            cmd = [agent_cli, "--prompt", "-"]
            if sandbox:
                cmd.extend(["--disallowedTools", "Edit,Write,Bash"])
            return CommandSpec(cmd=cmd, input_text=prompt, env=None)
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

    def _extract_json_from_file_reference(self, content: str) -> dict | list | None:
        pattern = re.compile(r"`?(?P<path>/[^\s`]+\.json)`?")
        for match in pattern.finditer(content):
            candidate = Path(match.group("path"))
            try:
                resolved = candidate.resolve()
            except FileNotFoundError:
                self._log_debug(
                    "agent_bridge.json_file_reference_missing",
                    {"candidate": str(candidate)},
                )
                continue
            if not resolved.exists() or resolved.is_dir():
                self._log_debug(
                    "agent_bridge.json_file_reference_not_file",
                    {"resolved": str(resolved)},
                )
                continue
            if not self._is_safe_json_path(resolved):
                self._log_debug(
                    "agent_bridge.json_file_reference_unsafe",
                    {"resolved": str(resolved)},
                )
                continue
            try:
                data = json.loads(resolved.read_text(encoding="utf-8"))
                self._log_debug(
                    "agent_bridge.json_file_reference_loaded",
                    {
                        "resolved": str(resolved),
                        "size_bytes": resolved.stat().st_size,
                    },
                )
                return data
            except json.JSONDecodeError:
                self._log_debug(
                    "agent_bridge.json_file_reference_decode_error",
                    {"resolved": str(resolved)},
                )
                continue
        return None

    def _is_safe_json_path(self, path: Path) -> bool:
        resolved = path.resolve()
        allowed_roots: list[Path] = [self.repo_root.resolve()]
        for candidate in (Path("/tmp"), Path(tempfile.gettempdir())):
            try:
                allowed_roots.append(candidate.resolve())
            except FileNotFoundError:
                continue
        resolved_str = str(resolved)
        for root in allowed_roots:
            root_str = str(root)
            if resolved_str == root_str or resolved_str.startswith(f"{root_str}/"):
                return True
        return False

    def _log_debug(self, event: str, payload: dict | None) -> None:
        if not self._debug_enabled:
            return
        try:
            self._debug_file.parent.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._debug_file.open("a", encoding="utf-8") as handle:
                handle.write(f"[{timestamp}] {event}\n")
                if payload is not None:
                    handle.write(json.dumps(payload, ensure_ascii=True, indent=2))
                    handle.write("\n")
                handle.write("\n")
        except OSError:
            return
