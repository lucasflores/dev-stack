"""Tests for the pipeline runner orchestration logic."""
from __future__ import annotations

import json
from pathlib import Path

from dev_stack.pipeline.runner import PipelineRunner
from dev_stack.pipeline.stages import FailureMode, PipelineStage, StageContext, StageResult, StageStatus


def _make_stage(
    name: str,
    order: int,
    *,
    failure_mode: FailureMode,
    status: StageStatus,
    requires_agent: bool = False,
    duration_ms: int = 2,
) -> PipelineStage:
    def _executor(_: StageContext) -> StageResult:
        return StageResult(
            stage_name=name,
            status=status,
            failure_mode=failure_mode,
            duration_ms=duration_ms,
            output=f"{name}:{status.value}",
        )

    return PipelineStage(
        order=order,
        name=name,
        failure_mode=failure_mode,
        requires_agent=requires_agent,
        executor=_executor,
    )


def _parallel_executor(_: StageContext) -> StageResult:
    return StageResult(
        stage_name="lint",
        status=StageStatus.PASS,
        failure_mode=FailureMode.HARD,
        duration_ms=0,
    )


def test_runner_halts_on_hard_failure(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.FAIL),
        _make_stage("security", 3, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    result = runner.run()

    assert not result.success
    assert [stage.stage_name for stage in result.results] == ["lint", "test"]


def test_runner_force_allows_hard_failure(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.FAIL),
        _make_stage("security", 3, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    result = runner.run(force=True)

    assert not result.success  # FR-006: hard failure means not successful, even with --force
    assert [stage.stage_name for stage in result.results] == ["lint", "test", "security"]


def test_runner_soft_stage_warns_but_passes(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("docs", 2, failure_mode=FailureMode.SOFT, status=StageStatus.WARN),
        _make_stage("security", 3, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    result = runner.run()

    statuses = [stage.status for stage in result.results]
    assert result.success
    assert statuses == [StageStatus.PASS, StageStatus.WARN, StageStatus.PASS]


def test_runner_skips_agent_stage_when_unavailable(tmp_path: Path) -> None:
    called: list[str] = []

    def _agent_stage(_: StageContext) -> StageResult:  # pragma: no cover - should not be called
        called.append("docs")
        return StageResult(
            stage_name="docs",
            status=StageStatus.PASS,
            failure_mode=FailureMode.SOFT,
            duration_ms=1,
        )

    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        PipelineStage(
            order=2,
            name="docs",
            failure_mode=FailureMode.SOFT,
            requires_agent=True,
            executor=_agent_stage,
        ),
    ]
    runner = PipelineRunner(tmp_path, stages=stages, agent_bridge=_AlwaysUnavailableAgent())

    result = runner.run()

    assert not called
    assert result.results[-1].status == StageStatus.SKIP
    assert result.results[-1].skipped_reason == "coding agent unavailable"


def test_runner_idempotent_results(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS, duration_ms=10),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS, duration_ms=10),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    first = runner.run()
    second = runner.run()

    first_signature = [(stage.stage_name, stage.status) for stage in first.results]
    second_signature = [(stage.stage_name, stage.status) for stage in second.results]
    assert first_signature == second_signature


def test_runner_filters_unselected_stages(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    result = runner.run(stages=["lint"])

    assert result.results[1].status == StageStatus.SKIP
    assert result.results[1].skipped_reason == "filtered via --stage"


def test_runner_rejects_unknown_stage_selection(tmp_path: Path) -> None:
    runner = PipelineRunner(
        tmp_path,
        stages=[_make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS)],
    )

    try:
        runner.run(stages=["unknown"])
    except ValueError as exc:  # pragma: no cover - exercised for branch coverage
        assert "Unknown stage(s)" in str(exc)
    else:  # pragma: no cover - ensures failure if exception missing
        raise AssertionError("Expected ValueError for unknown stage")


def test_runner_removes_skip_flag_on_success(tmp_path: Path) -> None:
    skip_flag = tmp_path / ".dev-stack" / "pipeline-skipped"
    skip_flag.parent.mkdir(parents=True)
    skip_flag.write_text("pending", encoding="utf-8")
    runner = PipelineRunner(
        tmp_path,
        stages=[_make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS)],
    )

    result = runner.run()

    assert result.success
    assert not skip_flag.exists()


def test_run_parallel_executes_stages(monkeypatch, tmp_path: Path) -> None:
    class _FakeFuture:
        def __init__(self, value: StageResult) -> None:
            self._value = value

        def result(self) -> StageResult:
            return self._value

    class _FakeExecutor:
        def __init__(self, max_workers: int) -> None:  # pragma: no cover - trivial
            self.max_workers = max_workers

        def __enter__(self) -> _FakeExecutor:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, *args):
            return _FakeFuture(fn(*args))

    def _fake_as_completed(futures):
        for future in futures:
            yield future

    monkeypatch.setattr("dev_stack.pipeline.runner.ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr("dev_stack.pipeline.runner.as_completed", _fake_as_completed)

    runner = PipelineRunner(tmp_path)
    stage = PipelineStage(
        order=1,
        name="lint",
        failure_mode=FailureMode.HARD,
        requires_agent=False,
        executor=_parallel_executor,
    )
    context = StageContext(repo_root=tmp_path)

    results = runner._run_parallel([stage], context)

    assert results["lint"].status == StageStatus.PASS


def test_runner_persists_state_file(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)

    result = runner.run()

    assert result.success
    state_path = tmp_path / ".dev-stack" / "pipeline" / "last-run.json"
    assert state_path.exists()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["success"] is True
    assert payload["stages"], payload


class _AlwaysUnavailableAgent:
    def is_available(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# T007/T008: PipelineRunResult.warnings and hollow-pipeline detection
# ---------------------------------------------------------------------------


def test_runner_warnings_field_empty_by_default(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("typecheck", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 3, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run()

    assert result.warnings == []


def _make_skip_stage(name: str, order: int) -> PipelineStage:
    def _executor(_: StageContext) -> StageResult:
        return StageResult(
            stage_name=name,
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=0,
            skipped_reason=f"{name} not installed",
        )

    return PipelineStage(
        order=order,
        name=name,
        failure_mode=FailureMode.HARD,
        requires_agent=False,
        executor=_executor,
    )


def test_runner_hollow_pipeline_warning_when_core_stages_skip(tmp_path: Path) -> None:
    stages = [
        _make_skip_stage("lint", 1),
        _make_skip_stage("typecheck", 2),
        _make_skip_stage("test", 3),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run(force=True)

    assert len(result.warnings) == 1
    assert "No substantive validation" in result.warnings[0]
    assert "uv sync --extra dev" in result.warnings[0]


def test_runner_no_hollow_warning_when_some_core_stages_pass(tmp_path: Path) -> None:
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_skip_stage("typecheck", 2),
        _make_skip_stage("test", 3),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run()

    assert result.warnings == []


# ---------------------------------------------------------------------------
# T016: Hollow-pipeline guard fires only for genuine tool-missing skips
# ---------------------------------------------------------------------------

def _make_filter_skip_stage(name: str, order: int) -> PipelineStage:
    """Stage that produces a 'filtered via --stage' skip result directly."""
    def _executor(_: StageContext) -> StageResult:
        return StageResult(
            stage_name=name,
            status=StageStatus.SKIP,
            failure_mode=FailureMode.HARD,
            duration_ms=0,
            skipped_reason="filtered via --stage",
        )

    return PipelineStage(
        order=order,
        name=name,
        failure_mode=FailureMode.HARD,
        requires_agent=False,
        executor=_executor,
    )


def test_hollow_pipeline_no_warning_when_all_core_stages_filter_skipped(tmp_path: Path) -> None:
    """Bug 3: Advisory must NOT fire when all core stages are skipped by --stage filter."""
    stages = [
        _make_filter_skip_stage("lint", 1),
        _make_filter_skip_stage("typecheck", 2),
        _make_filter_skip_stage("test", 3),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run(force=True)

    assert result.warnings == [], (
        "Expected no advisory when all core stages are filter-skipped, "
        f"but got: {result.warnings}"
    )


def test_hollow_pipeline_warning_fires_for_tool_missing_skip(tmp_path: Path) -> None:
    """Bug 3 regression: Advisory must still fire for genuine tool-missing skips."""
    stages = [
        _make_skip_stage("lint", 1),        # tool-missing skip
        _make_skip_stage("typecheck", 2),   # tool-missing skip
        _make_skip_stage("test", 3),        # tool-missing skip
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run(force=True)

    assert len(result.warnings) == 1
    assert "No substantive validation" in result.warnings[0]


def test_hollow_pipeline_warning_fires_for_mixed_skip_reasons(tmp_path: Path) -> None:
    """Advisory fires if at least one core stage has a non-filter skip reason."""
    stages = [
        _make_filter_skip_stage("lint", 1),  # filter skip — should not trigger alone
        _make_skip_stage("typecheck", 2),    # tool-missing skip — triggers advisory
        _make_filter_skip_stage("test", 3),  # filter skip
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    result = runner.run(force=True)

    assert len(result.warnings) == 1
    assert "No substantive validation" in result.warnings[0]


# ---------------------------------------------------------------------------
# T018: _record_pipeline_run() writes as_of and stale fields
# ---------------------------------------------------------------------------

def test_record_pipeline_run_writes_as_of_and_stale_false_for_full_run(tmp_path: Path) -> None:
    """Bug 4: Full run must persist as_of and stale=False."""
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("typecheck", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 3, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    runner.run()

    state_path = tmp_path / ".dev-stack" / "pipeline" / "last-run.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert "as_of" in payload, "Expected 'as_of' field in last-run.json"
    assert isinstance(payload["as_of"], str) and len(payload["as_of"]) > 0
    assert payload["stale"] is False


def test_record_pipeline_run_writes_stale_true_for_stage_filtered_run(tmp_path: Path) -> None:
    """Bug 4: A --stage filtered run must persist stale=True."""
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    runner.run(stages=["lint"])  # test will be filter-skipped

    state_path = tmp_path / ".dev-stack" / "pipeline" / "last-run.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert payload["stale"] is True
    assert "as_of" in payload


def test_record_pipeline_run_writes_stale_true_for_aborted_run(tmp_path: Path) -> None:
    """Bug 4: An aborted (hard-fail) run must persist stale=True."""
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.FAIL),
        _make_stage("test", 2, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    runner.run()

    state_path = tmp_path / ".dev-stack" / "pipeline" / "last-run.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert payload["stale"] is True
    assert "as_of" in payload


def test_record_pipeline_run_as_of_matches_timestamp(tmp_path: Path) -> None:
    """as_of must always equal timestamp (same value, backward-compatible alias)."""
    stages = [
        _make_stage("lint", 1, failure_mode=FailureMode.HARD, status=StageStatus.PASS),
    ]
    runner = PipelineRunner(tmp_path, stages=stages)
    runner.run()

    state_path = tmp_path / ".dev-stack" / "pipeline" / "last-run.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert payload["as_of"] == payload["timestamp"]
