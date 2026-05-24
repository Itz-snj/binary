"""Small subprocess wrapper used by QA agents."""

from __future__ import annotations

import shlex
import subprocess


def run_command(cmd: str | list[str], cwd: str, timeout: int = 60, max_output_chars: int = 4000) -> dict:
    args = shlex.split(cmd) if isinstance(cmd, str) else cmd
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        stdout = (proc.stdout or "")[:max_output_chars]
        stderr = (proc.stderr or "")[:max_output_chars]
        return {
            "command": " ".join(args),
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "exit_code": None,
            "stdout": (exc.stdout or "")[:max_output_chars] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[:max_output_chars] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    except Exception as exc:
        return {
            "command": " ".join(args),
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc)[:max_output_chars],
            "timed_out": False,
        }
