"""Tests for the lab_context retrieval engine."""

import json
import os
import sys

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.task_schema import TaskSchema
from schemas.common_types import RiskLevel
from lab_context.retriever import (
	extract_keywords,
	match_context,
	format_context_for_prompt,
	ContextFragment,
	DEFAULT_MAX_CONTEXT_CHARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_task(name: str) -> TaskSchema:
	"""Load a task JSON file and convert to TaskSchema via IncidentInput."""
	from schemas.incident_input_schema import IncidentInput

	task_path = os.path.join(os.path.dirname(__file__), "..", "tasks", f"{name}.json")
	with open(task_path, "r") as f:
		raw = json.load(f)
	incident = IncidentInput.model_validate(raw)
	return incident.to_task_schema()


def _task_with_keywords(*keywords) -> TaskSchema:
	"""Build a minimal task that contains specific keywords for context matching."""
	return TaskSchema(
		task_id="test-kw",
		title=" ".join(keywords),
		objective="Test context matching for: " + " ".join(keywords),
		context=" ".join(keywords),
		constraints=[],
		allowed_tools=[],
		expected_output="out.md",
		risk_level=RiskLevel.LOW,
	)


# ---------------------------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------------------------

class TestExtractKeywords:
	def test_proxmox_keywords(self):
		task = _task_with_keywords("proxmox", "hypervisor", "vlan10")
		kw = extract_keywords(task)
		assert "proxmox" in kw
		assert "hypervisor" in kw
		assert "vlan10" in kw

	def test_firewall_task_keywords(self):
		task = _load_task("firewall_rule_update")
		kw = extract_keywords(task)
		assert "iptables" in kw or "firewall" in kw or "vlan" in kw

	def test_extracts_ips(self):
		task = _task_with_keywords("proxmox", "10.10.10.50", "10.10.20.100")
		kw = extract_keywords(task)
		ips = [k for k in kw if k[0].isdigit()]
		assert "10.10.10.50" in ips
		assert "10.10.20.100" in ips

	def test_agent_vm_keywords(self):
		task = _task_with_keywords("agent", "inference", "vlan20", "isolated")
		kw = extract_keywords(task)
		assert "agent" in kw
		assert "vlan20" in kw


# ---------------------------------------------------------------------------
# match_context — real infrastructure
# ---------------------------------------------------------------------------

class TestMatchContext:
	def test_proxmox_task_matches_proxmox_system(self):
		task = _task_with_keywords("proxmox", "hypervisor", "kvm")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "proxmox" in names, f"Expected proxmox in {names}"

	def test_vlan_task_matches_vlans(self):
		task = _task_with_keywords("vlan", "network", "segmentation")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "vlans" in names, f"Expected vlans in {names}"

	def test_firewall_task_matches_firewall(self):
		task = _task_with_keywords("firewall", "opnsense", "inter-vlan")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "firewall" in names, f"Expected firewall in {names}"

	def test_agent_task_matches_ai_vm(self):
		task = _task_with_keywords("agent", "inference", "vlan20")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "ai-vm" in names, f"Expected ai-vm in {names}"

	def test_laptop_task_matches_laptop(self):
		task = _task_with_keywords("laptop", "operator", "jumpbox")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "laptop" in names, f"Expected laptop in {names}"

	def test_all_fragments_have_content(self):
		task = _task_with_keywords("proxmox", "hypervisor", "vlan10")
		frags = match_context(task)
		for f in frags:
			assert len(f.content) > 0
			assert len(f.name) > 0
			assert f.score > 0

	def test_firewall_task_matches_vlans_by_keyword(self):
		"""The firewall task uses vlan keywords that match vlans.yaml."""
		task = _task_with_keywords("vlan", "routing", "firewall")
		frags = match_context(task)
		names = [f.name for f in frags]
		assert "vlans" in names or "firewall" in names, f"Expected vlan/firewall context in {names}"


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

class TestBudget:
	def test_stays_within_default_budget(self):
		task = _task_with_keywords("proxmox", "hypervisor", "vlan10", "kvm")
		frags = match_context(task)
		total = sum(len(f.content) + len(f.name) + 20 for f in frags)
		assert total <= DEFAULT_MAX_CONTEXT_CHARS, (
			f"Context {total} chars exceeds budget {DEFAULT_MAX_CONTEXT_CHARS}"
		)

	def test_small_budget_limits_fragments(self):
		task = _task_with_keywords("proxmox", "vlan", "firewall", "agent")
		frags_small = match_context(task, max_chars=500)
		frags_large = match_context(task, max_chars=10000)
		assert len(frags_small) <= len(frags_large)

	def test_zero_budget_returns_empty(self):
		task = _task_with_keywords("proxmox", "hypervisor")
		frags = match_context(task, max_chars=0)
		assert frags == []


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
	def test_no_match_returns_empty(self):
		task = TaskSchema(
			task_id="test-no-match",
			title="Completely unrelated task",
			objective="Do something that matches nothing",
			context="This context has no lab-specific terms whatsoever",
			constraints=[],
			allowed_tools=[],
			expected_output="output.txt",
			risk_level=RiskLevel.LOW,
		)
		frags = match_context(task)
		assert frags == []

	def test_empty_context_formats_to_empty_string(self):
		assert format_context_for_prompt([]) == ""


# ---------------------------------------------------------------------------
# format_context_for_prompt
# ---------------------------------------------------------------------------

class TestFormatPrompt:
	def test_proxmox_prompt_contains_ip(self):
		task = _task_with_keywords("proxmox", "hypervisor", "kvm")
		frags = match_context(task)
		prompt = format_context_for_prompt(frags)
		assert "=== LAB CONTEXT" in prompt
		assert "=== END LAB CONTEXT ===" in prompt
		assert "10.10.10.50" in prompt

	def test_firewall_prompt_contains_opnsense(self):
		task = _task_with_keywords("firewall", "opnsense", "inter-vlan")
		frags = match_context(task)
		prompt = format_context_for_prompt(frags)
		assert "OPNsense" in prompt or "opnsense" in prompt.lower()

	def test_vlan_prompt_contains_subnets(self):
		task = _task_with_keywords("vlan", "network", "segmentation")
		frags = match_context(task)
		prompt = format_context_for_prompt(frags)
		assert "10.10.10.0/24" in prompt or "10.10.20.0/24" in prompt

	def test_prompt_has_section_headers(self):
		task = _task_with_keywords("proxmox", "hypervisor")
		frags = match_context(task)
		prompt = format_context_for_prompt(frags)
		assert "### SYSTEM:" in prompt or "### NETWORK:" in prompt
