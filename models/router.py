from __future__ import annotations

from models.base import BaseModelAdapter
from models.mock_adapter import MockModelAdapter
from models.local_adapter import LocalModelAdapter
from models.cloud_adapter import CloudModelAdapter


ROLE_MODEL_MAP: dict[str, str] = {
    "planner": "local",
    "executor": "local",
    "verifier": "cloud",
}

_ADAPTER_MAP: dict[str, type[BaseModelAdapter]] = {
    "mock": MockModelAdapter,
    "local": LocalModelAdapter,
    "cloud": CloudModelAdapter,
}


def get_model_for_role(role: str) -> BaseModelAdapter:
    model_name = ROLE_MODEL_MAP.get(role)
    if model_name is None:
        raise ValueError(f"No model configured for role '{role}'")

    adapter_cls = _ADAPTER_MAP.get(model_name)
    if adapter_cls is None:
        raise ValueError(f"No adapter registered for model '{model_name}'")

    return adapter_cls()
