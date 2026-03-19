from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelRequest:
    role: str
    system_prompt: str
    user_prompt: str


class BaseModelAdapter(ABC):
    @abstractmethod
    def generate(self, request: ModelRequest) -> str: ...
