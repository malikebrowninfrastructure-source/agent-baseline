from __future__ import annotations

import os


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

PLANNER_MODEL = os.getenv("PLANNER_MODEL", "qwen2.5-coder:7b")
EXECUTOR_MODEL = os.getenv("EXECUTOR_MODEL", "qwen2.5-coder:7b")
VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "llama3.1:8b")

CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "anthropic")
CLOUD_MODEL = os.getenv("CLOUD_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

