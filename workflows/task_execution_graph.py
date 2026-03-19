from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from agents_runtime import PlannerAgent, ExecutorAgent, VerifierAgent
from runtime.state import RunState
from schemas.common_types import Verdict, WorkflowStage, FinalStatus


def plan_node(state: RunState) -> dict:
    plan = PlannerAgent().run(task=state.task)
    return {
        "current_stage": WorkflowStage.PLANNING,
        "plan": plan,
    }


def execute_node(state: RunState) -> dict:
    execution = ExecutorAgent().run(
        task=state.task,
        plan=state.plan,
        run_id=state.run_id,
    )
    return {
        "current_stage": WorkflowStage.EXECUTION,
        "execution": execution,
    }


def verify_node(state: RunState) -> dict:
    if state.execution is None:
        raise ValueError("verify_node called without execution output in state")

    verification = VerifierAgent().run(
        task=state.task,
        plan=state.plan,
        execution=state.execution,
    )
    return {
        "current_stage": WorkflowStage.VERIFICATION,
        "verification": verification,
    }


def finalize_node(state: RunState) -> dict:
    if state.verification is None:
        return {
            "current_stage": WorkflowStage.FAILED,
            "final_status": FinalStatus.FAILED,
            "final_summary": "Run ended without verification output.",
        }

    verdict_to_status = {
        Verdict.PASS: FinalStatus.SUCCESS,
        Verdict.FAIL: FinalStatus.FAILED,
        Verdict.RETRY: FinalStatus.PARTIAL,
        Verdict.ESCALATE: FinalStatus.ESCALATED,
    }

    final_status = verdict_to_status.get(state.verification.verdict, FinalStatus.FAILED)

    return {
        "current_stage": WorkflowStage.COMPLETE,
        "final_status": final_status,
        "final_summary": (
            f"Run completed with verification verdict "
            f"'{state.verification.verdict.value}' and final status "
            f"'{final_status.value}'."
        ),
    }


def route_after_verification(state: RunState) -> str:
    if state.verification and state.verification.verdict == Verdict.RETRY:
        return "execute"
    return "finalize"


def build_graph():
    graph = StateGraph(RunState)

    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("verify", verify_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "verify")
    graph.add_conditional_edges(
        "verify",
        route_after_verification,
        {
            "execute": "execute",
            "finalize": "finalize",
        },
    )
    graph.add_edge("finalize", END)

    return graph.compile()
