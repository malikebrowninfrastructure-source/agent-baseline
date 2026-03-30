from __future__ import annotations

import json
from pathlib import Path

from .workflow_template_schema import WorkflowTemplate
from .workflow_output_schema import WorkflowOutput


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_cache: dict[str, WorkflowTemplate] = {}


def load_template(template_id: str) -> WorkflowTemplate:
	if template_id in _cache:
		return _cache[template_id]
	path = _TEMPLATE_DIR / f"{template_id}.json"
	if not path.exists():
		raise FileNotFoundError(f"Template not found: {path}")
	data = json.loads(path.read_text(encoding="utf-8"))
	template = WorkflowTemplate.model_validate(data)
	_cache[template_id] = template
	return template


def validate_output_against_template(
	output: WorkflowOutput,
	template: WorkflowTemplate,
) -> list[str]:
	"""Validate a WorkflowOutput against a template. Returns list of errors (empty = valid)."""
	errors: list[str] = []
	output_dict = output.model_dump()

	for req in template.required_sections:
		section_name = req.section_name
		if section_name not in output_dict:
			if req.required:
				errors.append(f"Missing required section: {section_name}")
			continue

		value = output_dict[section_name]
		if req.min_items is not None and isinstance(value, list):
			if len(value) < req.min_items:
				errors.append(
					f"Section '{section_name}' has {len(value)} items, "
					f"minimum required: {req.min_items}"
				)

	return errors
