Tool Registry and Controlled Tool Execution

## Objective

Replace direct tool calls with a registry-based execution model.

This step moved the system from:

- workflow calling helper functions directly

to:

- workflow calling tools through a controlled registry

## What Was Implemented

### Tool Registry
Created a registry layer that maps tool names to callable implementations.

Examples:
- `write_text_file`
- `write_json_file`
- `write_run_summary`

### Tool Class Mapping
Added logical tool classes to constrain which concrete tools are allowed for a task.

Examples:
- `file_tools`
- `validation_tools`

### Permission Enforcement
Introduced checks to ensure a task can only execute tools that belong to its allowed tool classes.

### Execution Logging
Updated execution output to record actual concrete tools used, rather than only allowed tool categories.

## Why This Matters

This introduced a real execution boundary between:

- orchestration logic
- tool implementation

It also established the foundation for:
- safer execution
- future sandboxing
- future backend routing

## Result

The workflow no longer depends directly on implementation-specific file helpers.

It now resolves tools through a registry and executes them in a controlled, auditable way.
