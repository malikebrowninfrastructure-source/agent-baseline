# in a python shell at the project root
from models.local_adapter import LocalModelAdapter
from models.base import ModelRequest

adapter = LocalModelAdapter("qwen2.5-coder:7b")
try:
    result = adapter.generate(ModelRequest(role="test", system_prompt="", user_prompt="ping"))
    print("local OK:", result[:80])
except RuntimeError as e:
    print("local unavailable:", e)
