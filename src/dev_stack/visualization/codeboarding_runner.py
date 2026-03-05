"""CodeBoarding CLI subprocess runner."""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import CodeBoardingError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RunResult:
    """Result of a CodeBoarding CLI invocation."""

    success: bool
    stdout: str
    stderr: str
    return_code: int


def check_cli_available() -> bool:
    """Return *True* if the ``codeboarding`` CLI is on PATH."""

    return shutil.which("codeboarding") is not None


def run(
    repo_root: Path,
    depth_level: int = 2,
    *,
    incremental: bool = False,
    timeout: int = 300,
) -> RunResult:
    """Invoke the CodeBoarding CLI as a subprocess.

    Parameters
    ----------
    repo_root:
        Repository root to analyse.
    depth_level:
        Component decomposition depth (``--depth-level``).
    incremental:
        If *True*, pass ``--incremental`` to CodeBoarding.
    timeout:
        Subprocess timeout in seconds.

    Returns
    -------
    RunResult
        Wraps stdout, stderr, return code and a success flag.

    Raises
    ------
    CodeBoardingError
        If the subprocess times out.
    """

    cmd: list[str] = [
        "codeboarding",
        "--local",
        str(repo_root),
        "--depth-level",
        str(depth_level),
    ]
    if incremental:
        cmd.append("--incremental")

    logger.debug("Running CodeBoarding: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=repo_root,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode() if exc.stderr else "")
        raise CodeBoardingError(
            f"CodeBoarding timed out after {timeout}s",
            stderr=stderr,
        ) from exc

    return RunResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )
