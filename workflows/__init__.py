# workflows/__init__.py

"""
Workflows package for defining and managing task execution graphs.
This package includes the core logic for building and executing workflow graphs,
as well as the definitions of workflow stages and related utilities.
"""



from .task_execution_graph import build_graph

__all__ = ["build_graph"]