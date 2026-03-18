# runtime/__init__.py

"""
The runtime package provides tools for managing and tracking the state of workflows during their execution.

It exposes the core RunState object, which is used across the system to represent and manipulate the current state of a workflow, including its progress, context, and transitions.
"""
from .state import RunState

__all__ = ["RunState"]

