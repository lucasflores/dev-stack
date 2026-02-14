"""Pipeline orchestrator for dev-stack."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .agent_bridge import AgentBridge
from .stages import (
    FailureMode,
    PipelineStage,
    StageContext,
    StageResult,
    StageStatus,
    build_pipeline_stages,
)
from ..manifest import ISO_FORMAT

DEFAULT_PARALLEL_THRESHOLD = 500
PARALLEL_STAGE_NAMES = {"lint", "test", "security"}
SKIP_FLAG_RELATIVE = Path(".dev-stack") / "pipeline-skipped"
PIPELINE_STATE_FILE = Path(".dev-stack") / "pipeline" / "last-run.json"


@dataclass(slots=True)
class PipelineRunResult:
    """Aggregate outcome of a pipeline invocation."""

    results: list[StageResult]
    success: bool
    aborted_stage: str | None = None
    skip_flag_detected: bool = False
    parallelized: bool = False


class PipelineRunner:
    """Coordinate execution of pipeline stages."""

    def __init__(
        self,
        repo_root: Path,
        *,
        agent_bridge: AgentBridge | None = None,
        manifest=None,
        stages: Sequence[PipelineStage] | None = None,
        parallel_threshold: int = DEFAULT_PARALLEL_THRESHOLD,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.agent_bridge = agent_bridge or AgentBridge(self.repo_root)
        self.manifest = manifest
        self._stages = list(stages) if stages else None
        self.parallel_threshold = parallel_threshold
        self._skip_flag_path = self.repo_root / SKIP_FLAG_RELATIVE

    def run(self, *, force: bool = False, stages: Sequence[str] | None = None) -> PipelineRunResult:
        """Execute the pipeline and return detailed results."""

        selection = {name.lower() for name in stages} if stages else None
        stage_defs = list(self._stages or build_pipeline_stages())
        self._assert_valid_selection(selection, stage_defs)

        file_count = self._count_project_files()
        base_context = StageContext(
            repo_root=self.repo_root,
            manifest=self.manifest,
            force=force,
            agent_bridge=self.agent_bridge,
            completed_results=[],
        )
        results: list[StageResult] = []
        aborted_stage: str | None = None
        abort_requested = False
        skip_flag_detected = self._skip_flag_path.exists()

        parallelizable = file_count > self.parallel_threshold
        parallel_results: dict[str, StageResult] = {}
        processed_parallel: set[str] = set()
        if parallelizable:
            filtered = [
                stage
                for stage in stage_defs
                if stage.name in PARALLEL_STAGE_NAMES and self._should_run(stage, selection)
            ]
            if filtered:
                parallel_results = self._run_parallel(filtered, base_context.without_agent())
                processed_parallel = set(parallel_results.keys())

        for stage in stage_defs:
            base_context.completed_results = list(results)
            if abort_requested and stage.name not in processed_parallel:
                break
            if selection and stage.name not in selection:
                results.append(self._skip_due_to_filter(stage))
                continue
            if stage.name in processed_parallel:
                result = parallel_results[stage.name]
            else:
                if stage.requires_agent and not self._agent_available():
                    result = self._skip_agent(stage)
                else:
                    result = self._execute_stage(stage, base_context)
            results.append(result)
            if (
                not force
                and stage.failure_mode == FailureMode.HARD
                and result.status == StageStatus.FAIL
            ):
                aborted_stage = stage.name
                abort_requested = True

        success = aborted_stage is None or force
        if success and self._skip_flag_path.exists():
            self._skip_flag_path.unlink()

        summary = PipelineRunResult(
            results=results,
            success=success,
            aborted_stage=aborted_stage,
            skip_flag_detected=skip_flag_detected,
            parallelized=bool(processed_parallel),
        )
        self._record_pipeline_run(summary)
        return summary

    # ------------------------------------------------------------------
    def _execute_stage(self, stage: PipelineStage, context: StageContext) -> StageResult:
        start = time.perf_counter()
        result = stage.executor(context)
        duration = int((time.perf_counter() - start) * 1000)
        if result.duration_ms == 0:
            result.duration_ms = duration
        return result

    def _run_parallel(
        self, stages: Sequence[PipelineStage], context: StageContext
    ) -> dict[str, StageResult]:
        results: dict[str, StageResult] = {}
        with ProcessPoolExecutor(max_workers=len(stages)) as executor:
            future_map = {
                executor.submit(_run_stage_in_subprocess, stage, context): stage.name for stage in stages
            }
            for future in as_completed(future_map):
                result = future.result()
                results[result.stage_name] = result
        return results

    def _should_run(self, stage: PipelineStage, selection: set[str] | None) -> bool:
        if not selection:
            return True
        return stage.name in selection

    def _skip_due_to_filter(self, stage: PipelineStage) -> StageResult:
        return StageResult(
            stage_name=stage.name,
            status=StageStatus.SKIP,
            failure_mode=stage.failure_mode,
            duration_ms=0,
            skipped_reason="filtered via --stage",
        )

    def _skip_agent(self, stage: PipelineStage) -> StageResult:
        return StageResult(
            stage_name=stage.name,
            status=StageStatus.SKIP,
            failure_mode=stage.failure_mode,
            duration_ms=0,
            skipped_reason="coding agent unavailable",
        )

    def _agent_available(self) -> bool:
        try:
            return self.agent_bridge.is_available()
        except Exception:
            return False

    def _count_project_files(self) -> int:
        ignored_dirs = {".git", ".dev-stack", ".venv", "node_modules", "__pycache__"}
        count = 0
        for root, dirs, files in os.walk(self.repo_root):
            rel = Path(root).relative_to(self.repo_root)
            if rel.parts and rel.parts[0] in ignored_dirs:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            count += len(files)
        return count

    def _assert_valid_selection(
        self, selection: set[str] | None, stage_defs: Sequence[PipelineStage]
    ) -> None:
        if not selection:
            return
        defined = {stage.name for stage in stage_defs}
        invalid = selection - defined
        if invalid:
            available = ", ".join(sorted(defined))
            raise ValueError(
                f"Unknown stage(s): {', '.join(sorted(invalid))}. Available stages: {available}."
            )

    def _record_pipeline_run(self, summary: PipelineRunResult) -> None:
        state_path = self.repo_root / PIPELINE_STATE_FILE
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": datetime.now(timezone.utc).strftime(ISO_FORMAT),
                "success": summary.success,
                "aborted_stage": summary.aborted_stage,
                "skip_flag_detected": summary.skip_flag_detected,
                "parallelized": summary.parallelized,
                "stages": [
                    {
                        "name": result.stage_name,
                        "status": result.status.value,
                        "failure_mode": result.failure_mode.value,
                        "duration_ms": result.duration_ms,
                        "output": result.output,
                        "skipped_reason": result.skipped_reason,
                    }
                    for result in summary.results
                ],
            }
            state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass


def _run_stage_in_subprocess(stage: PipelineStage, context: StageContext) -> StageResult:
    return stage.executor(context)
