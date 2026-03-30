"""Tests for the grounding validator — detects fabricated output."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from grounding.validator import (
	extract_claims,
	collect_sourced_facts,
	validate_grounding,
	GroundingViolation,
)
from schemas.task_schema import TaskSchema
from schemas.common_types import RiskLevel
from lab_context.retriever import ContextFragment, match_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_task(name: str) -> TaskSchema:
	from schemas.incident_input_schema import IncidentInput
	task_path = os.path.join(os.path.dirname(__file__), "..", "tasks", f"{name}.json")
	with open(task_path, "r") as f:
		raw = json.load(f)
	incident = IncidentInput.model_validate(raw)
	return incident.to_task_schema()


def _minimal_task(**overrides) -> TaskSchema:
	defaults = dict(
		task_id="test-001",
		title="Test task",
		objective="Do something",
		context="No specific context",
		constraints=[],
		allowed_tools=[],
		expected_output="out.md",
		risk_level=RiskLevel.LOW,
	)
	defaults.update(overrides)
	return TaskSchema(**defaults)


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------

class TestExtractClaims:
	def test_extracts_ipv4(self):
		text = "Connect to the switch at 192.168.1.100 on port 443"
		claims = extract_claims(text)
		ips = [c for c in claims if c[0] == "ipv4"]
		assert len(ips) == 1
		assert ips[0][1] == "192.168.1.100"

	def test_extracts_multiple_ips(self):
		text = "Primary: 10.0.1.1, Secondary: 10.0.1.2"
		claims = extract_claims(text)
		ips = [c[1] for c in claims if c[0] == "ipv4"]
		assert "10.0.1.1" in ips
		assert "10.0.1.2" in ips

	def test_extracts_credentials(self):
		text = "Login with admin:admin123 or root/password"
		claims = extract_claims(text)
		creds = [c for c in claims if c[0] == "credential"]
		assert len(creds) >= 1

	def test_extracts_device_models(self):
		text = "The switch is a Cisco Catalyst 2960"
		claims = extract_claims(text)
		models = [c for c in claims if c[0] == "device_model"]
		assert len(models) == 1
		assert "Cisco" in models[0][1]

	def test_no_claims_in_clean_text(self):
		text = "Check the ARP table and scan the local subnet for devices."
		claims = extract_claims(text)
		assert len(claims) == 0

	def test_extracts_multiple_vendors(self):
		text = "Could be Cisco or Juniper or Ubiquiti equipment"
		claims = extract_claims(text)
		models = [c for c in claims if c[0] == "device_model"]
		assert len(models) == 3


# ---------------------------------------------------------------------------
# collect_sourced_facts
# ---------------------------------------------------------------------------

class TestCollectSourcedFacts:
	def test_includes_task_ips(self):
		task = _minimal_task(context="Server at 10.0.1.50 is down")
		facts = collect_sourced_facts(task, [])
		assert "10.0.1.50" in facts

	def test_includes_context_fragment_ips(self):
		task = _minimal_task()
		frag = ContextFragment(
			source_file="test.yaml",
			kind="system",
			name="test-system",
			score=1,
			content="IP: 10.0.20.5",
		)
		facts = collect_sourced_facts(task, [frag])
		assert "10.0.20.5" in facts

	def test_empty_when_no_specifics(self):
		task = _minimal_task()
		facts = collect_sourced_facts(task, [])
		# Should have no IPs
		ips = [f for f in facts if f[0].isdigit()]
		assert len(ips) == 0


# ---------------------------------------------------------------------------
# validate_grounding
# ---------------------------------------------------------------------------

class TestValidateGrounding:
	def test_fabricated_ip_flagged(self):
		task = _minimal_task(context="Need to access switch web interface")
		output = "Navigate to 192.168.1.1 to access the switch management UI"
		violations = validate_grounding(output, task, [])
		assert len(violations) >= 1
		assert any(v.claim_type == "ipv4" for v in violations)

	def test_sourced_ip_passes(self):
		task = _minimal_task(context="Switch is at 10.0.1.50")
		output = "Connect to the switch at 10.0.1.50"
		violations = validate_grounding(output, task, [])
		ip_violations = [v for v in violations if v.claim_type == "ipv4"]
		assert len(ip_violations) == 0

	def test_credentials_always_flagged(self):
		task = _minimal_task(context="Switch at 10.0.1.50")
		output = "Login with admin:admin123"
		violations = validate_grounding(output, task, [])
		cred_violations = [v for v in violations if v.claim_type == "credential"]
		assert len(cred_violations) >= 1

	def test_unsourced_device_model_flagged(self):
		task = _minimal_task(context="Need to access the switch")
		output = "The switch is a Cisco Catalyst 2960-X"
		violations = validate_grounding(output, task, [])
		model_violations = [v for v in violations if v.claim_type == "device_model"]
		assert len(model_violations) >= 1

	def test_clean_output_passes(self):
		task = _minimal_task(context="Need to access the switch")
		output = (
			"Step 1: Check ARP table with arp -a\n"
			"Step 2: Scan local subnet for web interfaces\n"
			"Step 3: Document findings"
		)
		violations = validate_grounding(output, task, [])
		assert len(violations) == 0

	def test_context_fragment_ip_passes(self):
		task = _minimal_task()
		frag = ContextFragment(
			source_file="test.yaml",
			kind="system",
			name="router",
			score=1,
			content="Gateway: 10.0.1.1",
		)
		output = "Check the gateway at 10.0.1.1"
		violations = validate_grounding(output, task, [frag])
		ip_violations = [v for v in violations if v.claim_type == "ipv4"]
		assert len(ip_violations) == 0


# ---------------------------------------------------------------------------
# Integration: access_switch_ui task
# ---------------------------------------------------------------------------

class TestAccessSwitchIntegration:
	def test_switch_task_grounding_runs_without_error(self):
		"""Grounding validation should complete cleanly on switch task (no procedures needed)."""
		task = _load_task("access_switch_ui")
		frags = match_context(task)
		# Task may or may not match context fragments — the key assertion is no crash
		result = validate_grounding("Step 1: discover hosts on 10.10.0.0/24", task, frags)
		assert isinstance(result, list)

	def test_fabricated_switch_report_fails_grounding(self):
		"""Simulate the fabricated output and verify the validator catches it."""
		task = _load_task("access_switch_ui")
		frags = match_context(task)
		# This mimics the kind of fabricated output the system previously generated
		fabricated_output = (
			"## Switch Access Report\n"
			"The switch is a Cisco Catalyst 2960-X located at 10.0.1.1.\n"
			"Management VLAN is VLAN 99.\n"
			"Login with admin:admin123 via https://10.0.1.1\n"
			"Switch is healthy and all ports are operational.\n"
		)
		violations = validate_grounding(fabricated_output, task, frags)
		assert len(violations) >= 2, (
			f"Expected at least 2 violations, got {len(violations)}: "
			f"{[(v.claim_type, v.claim_value) for v in violations]}"
		)
		types = {v.claim_type for v in violations}
		assert "ipv4" in types or "credential" in types or "device_model" in types

	def test_discovery_output_passes_grounding(self):
		"""A proper discovery-first output should pass grounding checks."""
		task = _load_task("access_switch_ui")
		frags = match_context(task)
		safe_output = (
			"## Switch Discovery Workflow\n"
			"Step 1: Run ip addr to identify current subnet\n"
			"Step 2: Check ARP table with arp -a\n"
			"Step 3: Check OPNsense DHCP leases for switch entries\n"
			"Step 4: Scan subnet for web management ports\n"
			"Step 5: If candidate found, verify with curl\n"
			"Unknown: Switch IP, switch model, credentials source\n"
		)
		violations = validate_grounding(safe_output, task, frags)
		assert len(violations) == 0, (
			f"Safe output should pass, got violations: "
			f"{[(v.claim_type, v.claim_value) for v in violations]}"
		)
