from __future__ import annotations

import requests

from config import ANTHROPIC_API_KEY, CLOUD_MODEL
from models.base import BaseModelAdapter, ModelRequest


class CloudModelAdapter(BaseModelAdapter):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or CLOUD_MODEL

    def generate(self, request: ModelRequest) -> str:
        if not ANTHROPIC_API_KEY:
            return "[CLOUD MODEL FALLBACK] Missing ANTHROPIC_API_KEY"

        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "max_tokens": 800,
            "system": request.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": request.user_prompt,
                }
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            content = data.get("content", [])
            text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
            return "\n".join(text_blocks).strip()

        except Exception as exc:
            return f"[CLOUD MODEL FALLBACK] model={self.model_name} error={exc}"