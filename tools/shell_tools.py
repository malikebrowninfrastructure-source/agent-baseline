from __future__ import annotations

import subprocess

from tools.file_tools import ensure_run_dir


def run_shell_command(run_id: str, command: str) -> str:
    """
    Runs a shell command scoped to the run's output directory.
    Returns stdout. Raises RuntimeError on non-zero exit.
    Routed through OpenShellExecutor.
    """
    run_dir = ensure_run_dir(run_id)
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(run_dir),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Shell command failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def run_sandboxed_shell_command(run_id: str, command: str) -> str:
    """
    Placeholder for a sandboxed shell command.
    Always routed through SandboxExecutor, which raises NotImplementedError
    until a real sandbox backend (Docker, nsjail, etc.) is wired in.
    Do not call this function directly — use execute_tool() to enforce routing.
    """
    return run_shell_command(run_id, command)
