from __future__ import annotations

from models.base import BaseModelAdapter, ModelRequest


class LocalModelAdapter(BaseModelAdapter):
    def generate(self, request: ModelRequest) -> str:
        return (
            f"[LOCAL MODEL RESPONSE]\n"
            f"ROLE: {request.role}\n"
            f"Handled by local model backend.\n"
            f"SYSTEM: {request.system_prompt[:120]}\n"
            f"USER: {request.user_prompt[:200]}"
        )
