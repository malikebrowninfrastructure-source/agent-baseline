Agent Runtime Refactor

## Objective

Separate agent behavior from workflow orchestration.

This step moved the project from:

- inline workflow node logic

to:

- dedicated runtime agent modules

## What Was Implemented

Created an `agents_runtime/` package containing:

- `planner_agent.py`
- `executor_agent.py`
- `verifier_agent.py`

These modules now contain the role-specific runtime behavior for each stage.

## Architectural Shift

### Before
`workflows/task_execution_graph.py` contained most stage logic inline.

### After
`workflows/task_execution_graph.py` became a thinner orchestration layer that delegates behavior to:

- `run_planner(...)`
- `run_executor(...)`
- `run_verifier(...)`

## Why This Matters

This improved separation of concerns:

- `workflows/` now owns orchestration
- `agents_runtime/` now owns stage behavior

This makes the system easier to:
- modify
- test
- evolve into a true multi-agent runtime

## Result

LangGraph now orchestrates agent modules rather than inline business logic.
