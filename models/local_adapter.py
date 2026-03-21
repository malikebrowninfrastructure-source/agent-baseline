from __future__ import annotations

import requests
from langsmith import traceable

from config import OLLAMA_HOST, OLLAMA_KEEP_ALIVE
from models.base import BaseModelAdapter, ModelRequest


class LocalModelAdapter(BaseModelAdapter):
    def __init__(self, model_name: str):
        self.model_name = model_name

    @traceable(run_type="llm", name="ollama_generate")
    def generate(self, request: ModelRequest) -> str:
        url = f"{OLLAMA_HOST}/api/generate"

        prompt = (
            f"ROLE: {request.role}\n\n"
            f"SYSTEM:\n{request.system_prompt}\n\n"
            f"USER:\n{request.user_prompt}\n"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as exc:
            raise RuntimeError(f"Local model unavailable: model={self.model_name} error={exc}") from exc



