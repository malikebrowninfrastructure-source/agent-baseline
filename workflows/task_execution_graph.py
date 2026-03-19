from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from agents_runtime import PlannerAgent, ExecutorAgent, VerifierAgent
from runtime.state import RunState
from runtime.logging import utc_now_iso, make_event
from schemas.common_types import Verdict, WorkflowStage, FinalStatus


def plan_node(state: RunState) -> dict:
    plan = PlannerAgent().run(task=state.task)
    events = list(state.events)
    events.append(make_event("planning", "Planner completed successfully"))
    return {
        "current_stage": WorkflowStage.PLANNING,
        "plan": plan,
        "events": events,
    }


def execute_node(state: RunState) -> dict:
    execution = ExecutorAgent().run(
        task=state.task,
        plan=state.plan,
        run_id=state.run_id,
    )
    events = list(state.events)
    events.append(make_event("execution", "Executor completed successfully"))
    return {
        "current_stage": WorkflowStage.EXECUTION,
        "execution": execution,
        "verification": None,
        "final_status": None,
        "finished_at": None,
        "events": events,
    }


def verify_node(state: RunState) -> dict:
    if state.execution is None:
        raise ValueError("verify_node called without execution output in state")

    verification = VerifierAgent().run(
        task=state.task,
        plan=state.plan,
        execution=state.execution,
    )
    events = list(state.events)
    events.append(
        make_event(
            "verification",
            f"Verifier returned verdict '{verification.verdict.value}'",
        )
    )
    return {
        "current_stage": WorkflowStage.VERIFICATION,
        "verification": verification,
        "events": events,
    }


def finalize_node(state: RunState) -> dict:
    verification = state.verification
    events = list(state.events)

    if verification is None:
        events.append(make_event("finalization", "Run failed: verification output missing"))
        return {
            "current_stage": WorkflowStage.FAILED,
            "final_status": FinalStatus.FAILED,
            "final_summary": "Run ended without verification output.",
            "finished_at": utc_now_iso(),
            "events": events,
        }

    if verification.verdict == Verdict.RETRY:
        new_retry_count = state.retry_count + 1

        if new_retry_count > state.max_retries:
            events.append(
                make_event(
                    "finalization",
                    f"Retry limit exceeded ({new_retry_count - 1}/{state.max_retries}). Escalating run.",
                )
            )
            return {
                "current_stage": WorkflowStage.ESCALATED,
                "final_status": FinalStatus.ESCALATED,
                "final_summary": "Run escalated after exceeding retry threshold.",
                "retry_count": new_retry_count,
                "escalated": True,
                "finished_at": utc_now_iso(),
                "events": events,
            }

        events.append(
            make_event(
                "finalization",
                f"Run marked for retry ({new_retry_count}/{state.max_retries}).",
            )
        )
        return {
            "current_stage": WorkflowStage.FINALIZATION,
            "final_status": FinalStatus.PARTIAL,
            "final_summary": "Run requires retry before completion.",
            "retry_count": new_retry_count,
            "finished_at": utc_now_iso(),
            "events": events,
        }

    verdict_to_status = {
        Verdict.PASS: FinalStatus.SUCCESS,
        Verdict.FAIL: FinalStatus.FAILED,
        Verdict.ESCALATE: FinalStatus.ESCALATED,
    }

    final_status = verdict_to_status.get(verification.verdict, FinalStatus.FAILED)

    events.append(
        make_event(
            "finalization",
            f"Run completed with final status '{final_status.value}'.",
        )
    )
    return {
        "current_stage": WorkflowStage.COMPLETE,
        "final_status": final_status,
        "final_summary": (
            f"Run completed with verification verdict "
            f"'{verification.verdict.value}' and final status "
            f"'{final_status.value}'."
        ),
        "finished_at": utc_now_iso(),
        "events": events,
    }


def route_after_finalize(state: RunState) -> str:
    if state.final_status == FinalStatus.PARTIAL:
        return "execute"
    return "__end__"


def build_graph():
    graph = StateGraph(RunState)

    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("verify", verify_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "verify")
    graph.add_edge("verify", "finalize")
    graph.add_conditional_edges(
        "finalize",
        route_after_finalize,
        {
            "execute": "execute",
            "__end__": END,
        },
    )

    return graph.compile()
