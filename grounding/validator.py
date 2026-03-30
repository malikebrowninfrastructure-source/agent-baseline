"""Grounding validator — detects fabricated details in agent output.

Extracts claims (IPs, credentials, device models) from output text and
checks each against sourced facts from the task and retrieved lab context.
Unsourced claims are returned as GroundingViolations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from schemas.task_schema import TaskSchema
from lab_context.retriever import ContextFragment

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_IPV4_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")

_CREDENTIAL_RE = re.compile(
	r"(?:admin|root|password|passwd|username|login)\s*[:/=]\s*\S+",
	re.IGNORECASE,
)

# Matches hostnames with at least one dot (e.g. core-sw.lab.internal).
# Requires at least one letter to exclude pure version strings like "3.10.1".
_HOSTNAME_RE = re.compile(
	r"\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z][a-zA-Z0-9\-]*){1,})\b"
)

_DEVICE_MODEL_VENDORS = (
	"Cisco", "Juniper", "Ubiquiti", "Netgear", "MikroTik",
	"Arista", "HPE", "Dell", "TP-Link", "D-Link", "Meraki",
	"Fortinet", "Palo Alto", "SonicWall", "Ruckus", "Brocade",
)
_DEVICE_MODEL_RE = re.compile(
	r"\b(" + "|".join(re.escape(v) for v in _DEVICE_MODEL_VENDORS) + r")\s+\S+",
	re.IGNORECASE,
)

# Matches Python enum-like strings (e.g. WorkflowStage.DISCOVERY, Verdict.PASS).
# These appear in serialized execution output and are not real hostname claims.
_ENUM_LIKE_RE = re.compile(r'^[A-Z][a-zA-Z]+\.[A-Z][A-Z_]+$')


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GroundingViolation:
	claim_type: str        # "ipv4", "credential", "device_model"
	claim_value: str
	context_snippet: str   # surrounding text for diagnostics


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

def _snippet(text: str, start: int, end: int, margin: int = 40) -> str:
	"""Return a short snippet of *text* around [start, end]."""
	s = max(0, start - margin)
	e = min(len(text), end + margin)
	return text[s:e].replace("\n", " ")


def extract_claims(output_text: str) -> list[tuple[str, str, str]]:
	"""Extract (claim_type, claim_value, context_snippet) tuples from text."""
	claims: list[tuple[str, str, str]] = []

	# Track IP span positions so hostname check can skip overlapping matches.
	ip_spans: list[tuple[int, int]] = []
	for m in _IPV4_RE.finditer(output_text):
		ip = m.group(1)
		# Skip obvious non-address patterns (e.g. version numbers like 2.5.1.0)
		octets = ip.split(".")
		if all(0 <= int(o) <= 255 for o in octets):
			claims.append(("ipv4", ip, _snippet(output_text, m.start(), m.end())))
			ip_spans.append((m.start(), m.end()))

	for m in _CREDENTIAL_RE.finditer(output_text):
		claims.append(("credential", m.group(0), _snippet(output_text, m.start(), m.end())))

	for m in _DEVICE_MODEL_RE.finditer(output_text):
		claims.append(("device_model", m.group(0), _snippet(output_text, m.start(), m.end())))

	for m in _HOSTNAME_RE.finditer(output_text):
		hostname = m.group(1)
		# Skip matches that overlap with an already-captured IPv4 address.
		overlaps_ip = any(s <= m.start() < e or s < m.end() <= e for s, e in ip_spans)
		if overlaps_ip:
			continue
		# Skip Python enum-like strings (e.g. WorkflowStage.DISCOVERY).
		if _ENUM_LIKE_RE.match(hostname):
			continue
		claims.append(("hostname", hostname, _snippet(output_text, m.start(), m.end())))

	return claims


# ---------------------------------------------------------------------------
# Sourced facts collection
# ---------------------------------------------------------------------------

def collect_sourced_facts(
	task: TaskSchema,
	context_fragments: list[ContextFragment],
	discovery_results: dict | None = None,
) -> set[str]:
	"""Build a set of known IPs, hostnames, and vendor keywords from task, lab context,
	and optional live discovery output."""
	text_parts = [
		task.title,
		task.objective,
		task.context,
		" ".join(task.constraints),
	]
	for frag in context_fragments:
		text_parts.append(frag.content)

	# Include live discovery output as a source of facts
	if discovery_results:
		for host_label, commands in discovery_results.items():
			text_parts.append(host_label)
			for output in commands.values():
				if output and not output.startswith("[ERROR]"):
					text_parts.append(output)

	combined = " ".join(text_parts)

	facts: set[str] = set()
	# Extract all IPs present in sourced text
	for m in _IPV4_RE.finditer(combined):
		facts.add(m.group(1))

	# Extract vendor names present in sourced text
	for vendor in _DEVICE_MODEL_VENDORS:
		if vendor.lower() in combined.lower():
			facts.add(vendor.lower())

	# Extract hostnames present in sourced text
	for m in _HOSTNAME_RE.finditer(combined):
		hostname = m.group(1)
		if not _IPV4_RE.match(hostname):
			facts.add(hostname.lower())

	return facts


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_grounding(
	output_text: str,
	task: TaskSchema,
	context_fragments: list[ContextFragment],
	discovery_results: dict | None = None,
) -> list[GroundingViolation]:
	"""Check output_text for claims not supported by task or context.

	Returns a list of GroundingViolation for each unsourced claim.
	Credentials are always flagged — they should never appear in output.
	"""
	sourced = collect_sourced_facts(task, context_fragments, discovery_results)
	claims = extract_claims(output_text)

	violations: list[GroundingViolation] = []
	for claim_type, claim_value, snippet in claims:
		if claim_type == "credential":
			# Credentials are always flagged — they must never appear in output.
			violations.append(GroundingViolation(
				claim_type=claim_type,
				claim_value=claim_value,
				context_snippet=snippet,
			))
		elif claim_type == "ipv4":
			if claim_value not in sourced:
				violations.append(GroundingViolation(
					claim_type=claim_type,
					claim_value=claim_value,
					context_snippet=snippet,
				))
		elif claim_type == "device_model":
			# Check if the vendor part is in sourced facts
			vendor = claim_value.split()[0].lower() if claim_value else ""
			if vendor not in sourced:
				violations.append(GroundingViolation(
					claim_type=claim_type,
					claim_value=claim_value,
					context_snippet=snippet,
				))
		elif claim_type == "hostname":
			if claim_value.lower() not in sourced:
				violations.append(GroundingViolation(
					claim_type=claim_type,
					claim_value=claim_value,
					context_snippet=snippet,
				))

	return violations
