from __future__ import annotations

from models.base import BaseModelAdapter
from models.mock_adapter import MockModelAdapter


ROLE_MODEL_MAP: dict[str, str] = {
    "planner": "mock",
    "executor": "mock",
    "verifier": "mock",
}


def get_model_for_role(role: str) -> BaseModelAdapter:
    model_name = ROLE_MODEL_MAP.get(role)
    if model_name is None:
        raise ValueError(f"No model configured for role '{role}'")
    if model_name == "mock":
        return MockModelAdapter()
    raise ValueError(f"No adapter registered for model '{model_name}'")
