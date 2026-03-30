from __future__ import annotations

import re

from runtime.logging import utc_now_iso
from schemas.task_schema import TaskSchema
from schemas.common_types import RiskLevel, WorkflowCategory
from lab_context.retriever import match_context
from grounding.validator import validate_grounding
from schemas.workflow_output_schema import (
	WorkflowOutput,
	ClassificationSection,
	NavigationSection,
	DependencyEntry,
	WorkflowStep,
	ValidationStep,
	RollbackStep,
	PlaybookEntry,
)


def _infer_category(task: TaskSchema) -> WorkflowCategory:
	text = f"{task.title} {task.objective} {task.context}".lower()
	if any(kw in text for kw in ("troubleshoot", "diagnose", "outage", "502", "error", "unresp")):
		return WorkflowCategory.TROUBLESHOOTING
	if any(kw in text for kw in ("access", "credential", "permission", "password", "cert", "key rotation")):
		return WorkflowCategory.ACCESS_CHANGE
	return WorkflowCategory.CHANGE


def _infer_scope(task: TaskSchema) -> str:
	text = f"{task.context}".lower()
	if any(kw in text for kw in ("site", "all", "global", "cluster-wide")):
		return "site_wide"
	if any(kw in text for kw in ("vlan", "subnet", "network", "segment")):
		return "network_segment"
	return "single_host"


def _extract_systems(task: TaskSchema) -> list[str]:
	"""Extract system names from context heuristically."""
	systems = []
	words = task.context.replace(",", " ").replace(".", " ").split()
	for i, w in enumerate(words):
		if w.lower() in ("on", "from", "to") and i + 1 < len(words):
			candidate = words[i + 1].strip("()")
			if any(c in candidate for c in ("-", ".")):
				systems.append(candidate)
	if not systems:
		systems.append(task.title.split()[-1])
	return list(dict.fromkeys(systems))


def build_workflow_output(run_state_dict: dict, task: TaskSchema) -> WorkflowOutput:
	"""Build a WorkflowOutput from a completed run state dict and the original task."""
	plan = run_state_dict.get("plan", {}) or {}
	execution = run_state_dict.get("execution", {}) or {}
	verification = run_state_dict.get("verification", {}) or {}

	# --- classification ---
	category = _infer_category(task)
	classification = ClassificationSection(
		category=category,
		severity=task.risk_level,
		impact_scope=_infer_scope(task),
		change_type="standard" if category == WorkflowCategory.CHANGE else None,
	)

	# --- navigation ---
	systems = _extract_systems(task)
	navigation = NavigationSection(
		affected_systems=systems if systems else [task.title],
		affected_services=[task.expected_output],
		entry_point=task.objective,
	)

	# --- dependencies ---
	deps = []
	tools_used: set[str] = set(execution.get("tools_used") or [])
	required_tools = plan.get("required_tools") or task.allowed_tools
	for tool in required_tools:
		deps.append(DependencyEntry(name=tool, type="service", status="verified" if tool in tools_used else "assumed"))
	assumptions = plan.get("assumptions") or []
	for assumption in assumptions[:3]:
		deps.append(DependencyEntry(name=assumption, type="config", status="assumed"))
	if not deps:
		deps.append(DependencyEntry(name="baseline_system", type="service", status="assumed"))

	# --- workflow_steps ---
	exec_steps = plan.get("execution_steps") or [task.objective]
	workflow_steps = []
	for i, step in enumerate(exec_steps):
		workflow_steps.append(WorkflowStep(
			step_number=i + 1,
			action=step,
			expected_outcome="Step completed successfully",
			requires_approval=(i == 0 and task.risk_level != RiskLevel.LOW),
		))

	# --- risks ---
	risks = plan.get("risks") or ["Insufficient context may reduce output fidelity"]

	# --- validation_steps ---
	validation_steps = []
	issues = verification.get("issues_found") or []
	quality = verification.get("quality_assessment")
	if quality:
		validation_steps.append(ValidationStep(
			check="Quality assessment review",
			expected_result=quality,
			is_blocking=True,
		))
	for issue in issues:
		validation_steps.append(ValidationStep(
			check=f"Verify resolved: {issue}",
			expected_result="Issue resolved",
			is_blocking=True,
		))
	artifacts = execution.get("artifacts_created") or []
	for artifact in artifacts:
		validation_steps.append(ValidationStep(
			check=f"Verify artifact exists: {artifact}",
			expected_result="Artifact present and non-empty",
			is_blocking=True,
		))
	if not validation_steps:
		validation_steps.append(ValidationStep(
			check="Verify workflow completed successfully",
			expected_result="All steps executed without error",
			is_blocking=True,
		))

	# --- rollback_steps ---
	rollback_steps = []
	for i, ws in enumerate(workflow_steps):
		if ws.rollback_action:
			rollback_steps.append(RollbackStep(
				step_number=i + 1,
				action=ws.rollback_action,
				verification=f"Confirm step {ws.step_number} was reverted",
			))
	if not rollback_steps:
		rollback_steps.append(RollbackStep(
			step_number=1,
			action=f"Revert changes from: {task.title}",
			verification="Confirm system returned to pre-change state",
		))

	# --- documentation ---
	documentation = [
		f"Task: {task.title}",
		f"Objective: {task.objective}",
	]
	for constraint in task.constraints[:3]:
		documentation.append(f"Constraint: {constraint}")

	# --- known_facts / unknown_facts ---
	context_fragments = match_context(task)
	known_facts: list[str] = []
	unknown_facts: list[str] = []

	# Known: task context and constraints
	if task.context:
		known_facts.append(f"Task context: {task.context}")
	for constraint in task.constraints:
		known_facts.append(f"Constraint: {constraint}")
	# Known: matched lab context fragment names
	for frag in context_fragments:
		known_facts.append(f"Lab context matched: {frag.name} ({frag.kind})")

	# Unknown: detect gap keywords in task text that lack concrete values
	task_text = f"{task.title} {task.objective} {task.context}".lower()
	_GAP_KEYWORDS = {
		"ip": "IP address",
		"switch": "Switch identity/location",
		"credential": "Credentials",
		"password": "Credentials",
		"vlan": "VLAN assignment",
		"model": "Device model",
		"interface": "Network interface",
		"subnet": "Subnet/network range",
		"hostname": "Hostname",
	}
	# Check which gap keywords appear in task text but have no concrete values in context
	context_text = " ".join(f.content for f in context_fragments).lower()
	concrete_ips = set(re.findall(r"\d+\.\d+\.\d+\.\d+", task_text + " " + context_text))
	for keyword, label in _GAP_KEYWORDS.items():
		if keyword in task_text:
			# Check if there's a concrete value for this in context
			if keyword == "ip" and concrete_ips:
				continue
			if keyword in context_text:
				continue
			unknown_facts.append(f"{label} (referenced in task but no concrete value in context)")

	if not context_fragments:
		unknown_facts.append("No lab context matched — all environment details are unknown")

	# --- playbook_entry ---
	playbook_entry = PlaybookEntry(
		playbook_id=f"pb-{task.task_id}",
		title=task.title,
		last_updated=utc_now_iso(),
		linked_tasks=[task.task_id],
	)

	output = WorkflowOutput(
		classification=classification,
		navigation=navigation,
		dependencies=deps,
		workflow_steps=workflow_steps,
		risks=risks,
		validation_steps=validation_steps,
		rollback_steps=rollback_steps,
		documentation=documentation,
		playbook_entry=playbook_entry,
		known_facts=known_facts,
		unknown_facts=unknown_facts,
	)

	serialized = output.model_dump_json()
	grounding_violations = validate_grounding(serialized, task, context_fragments)
	if grounding_violations:
		violation_details = "; ".join(
			f"Fabricated {v.claim_type}: {v.claim_value}"
			for v in grounding_violations
		)
		raise ValueError(f"Grounding validation failed: {violation_details}")

	return output
