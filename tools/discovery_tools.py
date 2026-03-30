"""Read-only discovery tools for local and remote host interrogation.

Commands are validated against strict allowlists before execution.
Remote execution uses SSH with BatchMode (no interactive prompts).
All failures are non-fatal — errors are returned as strings.
"""
from __future__ import annotations

import os
import re
import subprocess

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

ALLOWED_LOCAL_CMDS = frozenset([
    "ip addr show",
    "ip route show",
    "arp -n",
    "hostname",
    "uname -a",
    "ss -tnlp",
    "cat /etc/hosts",
    "cat /etc/resolv.conf",
])

ALLOWED_REMOTE_CMDS = frozenset([
    "ip addr show",
    "ip route show",
    "arp -n",
    "hostname",
    "uname -a",
    "ss -tnlp",
    "docker ps",
    "cat /etc/hosts",
    "cat /etc/resolv.conf",
])

# Parameterized commands — base validated, argument sanitized separately.
_SYSTEMCTL_STATUS_BASE = "systemctl status"
_PING_BASE = "ping -c 1 -W 2"

_SAFE_SERVICE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*$")
_SAFE_HOST_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*$")

_DEFAULT_SSH_KEY = os.environ.get(
    "DISCOVERY_SSH_KEY",
    os.path.expanduser("~/.ssh/agent_discovery_ed25519"),
)

_SSH_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Command validation
# ---------------------------------------------------------------------------

def _validate_local_command(command: str) -> list[str]:
    """Validate and return the shell argv for a local command."""
    cmd = command.strip()
    if cmd in ALLOWED_LOCAL_CMDS:
        return cmd.split()
    # Parameterized: systemctl status <service>
    if cmd.startswith(_SYSTEMCTL_STATUS_BASE + " "):
        service = cmd[len(_SYSTEMCTL_STATUS_BASE) + 1:].strip()
        if not _SAFE_SERVICE_RE.match(service):
            raise ValueError(f"Unsafe service name in command: {command!r}")
        return ["systemctl", "status", service]
    # Parameterized: ping -c 1 -W 2 <host>
    if cmd.startswith(_PING_BASE + " "):
        host = cmd[len(_PING_BASE) + 1:].strip()
        if not _SAFE_HOST_RE.match(host):
            raise ValueError(f"Unsafe host in command: {command!r}")
        return ["ping", "-c", "1", "-W", "2", host]
    raise ValueError(f"Command not in local allowlist: {command!r}")


def _validate_remote_command(command: str) -> str:
    """Validate and return the remote command string for SSH."""
    cmd = command.strip()
    if cmd in ALLOWED_REMOTE_CMDS:
        return cmd
    # Parameterized: systemctl status <service>
    if cmd.startswith(_SYSTEMCTL_STATUS_BASE + " "):
        service = cmd[len(_SYSTEMCTL_STATUS_BASE) + 1:].strip()
        if not _SAFE_SERVICE_RE.match(service):
            raise ValueError(f"Unsafe service name in command: {command!r}")
        return f"systemctl status {service}"
    # Parameterized: ping -c 1 -W 2 <host>
    if cmd.startswith(_PING_BASE + " "):
        host = cmd[len(_PING_BASE) + 1:].strip()
        if not _SAFE_HOST_RE.match(host):
            raise ValueError(f"Unsafe host in command: {command!r}")
        return f"ping -c 1 -W 2 {host}"
    raise ValueError(f"Command not in remote allowlist: {command!r}")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_local_discovery(run_id: str, command: str) -> str:
    """Run a read-only discovery command on the local host.

    Returns the command output as a string, or an error string on failure.
    Never raises.
    """
    try:
        argv = _validate_local_command(command)
    except ValueError as exc:
        return f"[ERROR] {exc}"

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_SSH_TIMEOUT,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            stderr = result.stderr.strip()
            return f"[exit {result.returncode}] {output}\n{stderr}".strip()
        return output
    except subprocess.TimeoutExpired:
        return f"[ERROR] command timed out after {_SSH_TIMEOUT}s: {command!r}"
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"


def run_remote_discovery(
    run_id: str,
    host: str,
    command: str,
    ssh_user: str,
    ssh_port: int = 22,
    ssh_key: str | None = None,
) -> str:
    """Run a read-only discovery command on a remote host via SSH.

    Returns the command output as a string, or an error string on failure.
    Never raises.
    """
    try:
        remote_cmd = _validate_remote_command(command)
    except ValueError as exc:
        return f"[ERROR] {exc}"

    key_path = ssh_key or _DEFAULT_SSH_KEY

    ssh_argv = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={_SSH_TIMEOUT}",
        "-o", "StrictHostKeyChecking=no",
        "-i", key_path,
        "-p", str(ssh_port),
        f"{ssh_user}@{host}",
        remote_cmd,
    ]

    try:
        result = subprocess.run(
            ssh_argv,
            capture_output=True,
            text=True,
            timeout=_SSH_TIMEOUT,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            stderr = result.stderr.strip()
            return f"[exit {result.returncode}] {output}\n{stderr}".strip()
        return output
    except subprocess.TimeoutExpired:
        return f"[ERROR] SSH timed out after {_SSH_TIMEOUT}s connecting to {ssh_user}@{host}"
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"
