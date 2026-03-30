"""Discovery agent — runs read-only SSH and local commands to collect live system state.

Called before execution to inject real host facts into the executor prompt.
All failures are non-fatal; the run continues with an empty discovery result.
"""
from __future__ import annotations

import json
import os
import warnings

import yaml

from lab_context.retriever import match_context
from schemas.task_schema import TaskSchema
from tools.discovery_tools import run_local_discovery, run_remote_discovery

_REMOTE_COMMANDS = [
    "hostname",
    "ip addr show",
    "ip route show",
    "ss -tnlp",
    "docker ps",
]

_LOCAL_COMMANDS = [
    "hostname",
    "ip addr show",
    "ip route show",
    "ss -tnlp",
]


def _parse_system_targets(context_fragments) -> list[dict]:
    """Extract SSH connection details from kind=system context fragments."""
    targets = []
    for frag in context_fragments:
        if frag.kind != "system":
            continue
        try:
            doc = yaml.safe_load(frag.content)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        host_block = doc.get("host", {}) or {}
        management_ip = host_block.get("management_ip")
        ssh_block = host_block.get("ssh", {}) or {}
        ssh_user = ssh_block.get("user", "root")
        ssh_port = int(ssh_block.get("port", 22))
        if management_ip:
            targets.append({
                "name": frag.name,
                "ip": management_ip,
                "ssh_user": ssh_user,
                "ssh_port": ssh_port,
            })
    return targets


def run_discovery(task: TaskSchema, run_id: str) -> dict[str, dict[str, str]]:
    """Collect live state from matched hosts and the local machine.

    Returns {host_label: {command: output}}.
    Writes discovery_log.json to the run artifact directory.
    """
    context_fragments = match_context(task)
    targets = _parse_system_targets(context_fragments)

    results: dict[str, dict[str, str]] = {}

    # Remote discovery for each matched system
    ssh_key = os.environ.get(
        "DISCOVERY_SSH_KEY",
        os.path.expanduser("~/.ssh/agent_discovery_ed25519"),
    )
    for target in targets:
        label = f"{target['name']} ({target['ip']})"
        host_results: dict[str, str] = {}
        for cmd in _REMOTE_COMMANDS:
            output = run_remote_discovery(
                run_id=run_id,
                host=target["ip"],
                command=cmd,
                ssh_user=target["ssh_user"],
                ssh_port=target["ssh_port"],
                ssh_key=ssh_key,
            )
            host_results[cmd] = output
        results[label] = host_results

    # Local discovery on the AI VM itself
    local_results: dict[str, str] = {}
    for cmd in _LOCAL_COMMANDS:
        output = run_local_discovery(run_id=run_id, command=cmd)
        local_results[cmd] = output
    results["local"] = local_results

    # Write discovery log artifact
    try:
        runs_dir = os.path.join(os.path.dirname(__file__), "..", "runs", run_id)
        os.makedirs(runs_dir, exist_ok=True)
        log_path = os.path.join(runs_dir, "discovery_log.json")
        with open(log_path, "w") as f:
            json.dump(results, f, indent=2)
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"[discovery] failed to write discovery_log.json: {exc}", stacklevel=2)

    return results


class DiscoveryAgent:
    def run(self, task: TaskSchema, run_id: str) -> dict[str, dict[str, str]]:
        return run_discovery(task=task, run_id=run_id)
