from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BackendName = Literal["local", "cloud", "mock"]


@dataclass
class RoutingDecision:
    backend: BackendName
    reason: str


def estimate_prompt_size(text: str) -> int:
    # Cheap approximation: ~4 chars/token average for English-ish text
    return max(1, len(text) // 4)


def should_use_cloud_for_executor(
    risk_level: str,
    retry_count: int,
    token_estimate: int,
    externally_visible: bool = False,
) -> bool:
    if externally_visible:
        return True
    if risk_level == "high":
        return True
    if retry_count > 0:
        return True
    if token_estimate > 6000:
        return True
    return False


def route_role(
    role: str,
    risk_level: str,
    retry_count: int,
    token_estimate: int,
    externally_visible: bool = False,
) -> RoutingDecision:
    if role == "planner":
        return RoutingDecision(
            backend="local",
            reason="Planner defaults to local for cost efficiency.",
        )

    if role == "executor":
        if should_use_cloud_for_executor(
            risk_level=risk_level,
            retry_count=retry_count,
            token_estimate=token_estimate,
            externally_visible=externally_visible,
        ):
            return RoutingDecision(
                backend="cloud",
                reason="Executor escalated to cloud due to risk/retry/size/visibility.",
            )
        return RoutingDecision(
            backend="local",
            reason="Executor defaults to local for first-pass execution.",
        )

    if role == "verifier":
        return RoutingDecision(
            backend="local",
            reason="Verifier defaults to local for cost efficiency.",
        )

    return RoutingDecision(
        backend="mock",
        reason="Unknown role; falling back to mock backend.",
    )

