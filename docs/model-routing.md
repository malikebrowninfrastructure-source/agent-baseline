## Model Routing Hooks

## Objective

Introduce a model abstraction layer so agent behavior can be routed through role-specific backends.

This step prepared the system for future use of:

- local models
- cloud models
- fallback mock behavior

## What Was Implemented

Created a `models/` package with:

- `base.py`
- `mock_adapter.py`
- `local_adapter.py`
- `cloud_adapter.py`
- `router.py`

## Key Components

### BaseModelAdapter
Defines a common model interface:

- accepts a `ModelRequest`
- returns generated text

### ModelRequest
Carries:
- role
- system prompt
- user prompt

### Adapters
Added three backend adapters:

- `MockModelAdapter`
- `LocalModelAdapter`
- `CloudModelAdapter`

### Router
Created role-based selection logic so different agent roles can route to different model backends.

Examples:
- planner → local
- executor → local
- verifier → cloud

## Why This Matters

This decouples:

- agent behavior
from
- model provider selection

The graph and runtime agents no longer need to know which backend is serving the role.

## Result

The system is now model-adapter ready and can later be connected to real inference providers without redesigning orchestration.
