# Tool Policy

## Purpose
Define the allowed tool classes, access boundaries, and usage discipline for the baseline multi-agent system.

## Tool Classes

### 1. File Tools
Allowed Uses:
- read files needed for task execution
- write approved artifacts
- save run outputs

Disallowed Uses:
- arbitrary destructive file operations
- hidden file mutation
- writing outside approved project scope

### 2. Retrieval Tools
Allowed Uses:
- search approved project context
- retrieve relevant notes or documents
- support planning and verification

Disallowed Uses:
- unrestricted external retrieval unless explicitly approved
- retrieving unrelated context to expand scope

### 3. Execution Tools
Allowed Uses:
- run constrained commands or scripts
- perform approved execution steps
- support artifact generation or validation

Disallowed Uses:
- unrestricted shell access
- destructive system changes
- unauthorized network operations
- policy modification through execution

### 4. Validation Tools
Allowed Uses:
- validate schema
- lint outputs
- run safe tests
- verify structural correctness

Disallowed Uses:
- modifying artifacts while pretending only to validate
- passing results without reporting validation failures

## Agent-to-Tool Permissions

### Orchestrator
Allowed:
- retrieval tools
- artifact logging operations

Disallowed:
- execution tools
- implementation-focused file mutation

### Planner
Allowed:
- retrieval tools

Disallowed:
- execution tools
- direct artifact mutation
- validation masquerading as execution

### Executor
Allowed:
- file tools
- execution tools
- validation tools
- limited retrieval tools when required by the plan

Disallowed:
- policy changes
- unrestricted access
- self-approval of quality or safety

### Verifier
Allowed:
- retrieval tools
- validation tools
- artifact read operations

Disallowed:
- implementation execution
- hidden correction of outputs while reviewing them

## Tool Usage Rules
- every tool use should be attributable to a specific task need
- tool use must remain inside the current task scope
- tool failures must be recorded explicitly
- unavailable required tools must trigger retry or escalate logic
- agents must not imply a tool succeeded when it did not
