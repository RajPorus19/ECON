"""Local subprocess executor. Never uses shell=True by default."""

from __future__ import annotations

import subprocess

from core.execution import ExecuteRequest, ExecuteResult


class LocalSubprocessExecutor:
    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        try:
            completed = subprocess.run(  # noqa: S603 — argv list, shell=False
                request.argv,
                capture_output=True,
                text=True,
                timeout=request.timeout_s,
                cwd=request.cwd,
                shell=False,
                check=False,
            )
        except FileNotFoundError:
            return ExecuteResult(
                success=False,
                exit_code=127,
                error=f"executable not found: {request.argv[0] if request.argv else ''}",
            )
        except subprocess.TimeoutExpired:
            return ExecuteResult(success=False, error="timeout")
        except OSError as exc:
            return ExecuteResult(success=False, error=str(exc))

        return ExecuteResult(
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout[-8000:],
            stderr=completed.stderr[-8000:],
        )
