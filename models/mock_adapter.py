from __future__ import annotations

from models.base import BaseModelAdapter, ModelRequest


class MockModelAdapter(BaseModelAdapter):
    def generate(self, request: ModelRequest) -> str:
        return (
            f"[MOCK RESPONSE]\n"
            f"ROLE: {request.role}\n"
            f"SYSTEM: {request.system_prompt[:120]}\n"
            f"USER: {request.user_prompt[:200]}"
        )
