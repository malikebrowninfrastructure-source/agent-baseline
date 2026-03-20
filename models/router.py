

from __future__ import annotations

from config import PLANNER_MODEL, EXECUTOR_MODEL, VERIFIER_MODEL, CLOUD_MODEL
from models.base import BaseModelAdapter
from models.mock_adapter import MockModelAdapter
from models.local_adapter import LocalModelAdapter
from models.cloud_adapter import CloudModelAdapter


def get_model_adapter(backend: str, role: str) -> BaseModelAdapter:
    try:
        if backend == "local":
            if role == "planner":
                return LocalModelAdapter(model_name=PLANNER_MODEL)
            if role == "executor":
                return LocalModelAdapter(model_name=EXECUTOR_MODEL)
            if role == "verifier":
                return LocalModelAdapter(model_name=VERIFIER_MODEL)

        if backend == "cloud":
            return CloudModelAdapter(model_name=CLOUD_MODEL)

        return MockModelAdapter()

    except Exception:
        return MockModelAdapter()

