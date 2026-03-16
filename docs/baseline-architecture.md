# Baseline Architecture

## Mission
Build a secure-by-design, Python-based, stateful multi-agent workflow that accepts a structured engineering task, plans it, executes approved actions with constrained tools, verifies the result, and saves traceable artifacts.

---

## Scope
V1 includes:
- one controlled workflow
- four agents
- constrained tool usage
- structured input and output contracts
- traceable run artifacts
- basic verification before finalization

---

## Non-Goals
V1 does not include:
- multi-industry verticalization
- multi-tenant platform features
- advanced long-term memory
- unrestricted autonomous web behavior
- large agent swarms
- full enterprise production deployment
- self-improving autonomous behavior

---

## Agent Topology

1. Orchestrator
- Controls workflow routing and run lifecycle.

2. Planner
- Converts a task into a structured execution plan.

3. Executor
- Performs approved actions using constrained tools.

4. Verifier
- Reviews outputs and returns pass/fail style verdicts.

---

## Workflow

1. Intake task
2. Orchestrator validates task
3. Planner creates plan
4. Executor performs approved actions
5. Verifier reviews result
6. Orchestrator finalizes status
7. System saves run artifacts

---

## Canonical Task Type

Structured engineering task execution.

Examples:
- task analysis
- implementation planning
- constrained artifact generation
- limited tool-based execution
- output verification

---

## Tool Classes

1. File Tools
- Read files
- Write files
- Save artifacts

2. Retrieval Tools
- Search approved context
- Retrieve relevant documents

3. Execution Tools
- Run constrained commands or scripts

4. Validation Tools
- Validate schema
- Lint outputs
- Run tests

---

## Tool Permissions

Orchestrator:
- Allowed: retrieval tools, artifact logging
- Not allowed: execution tools

Planner:
- Allowed: retrieval tools
- Not allowed: execution tools

Executor:
- Allowed: file tools, execution tools, validation tools
- Not allowed: policy changes or unrestricted access

Verifier:
- Allowed: retrieval tools, validation tools
- Not allowed: implementation execution

---

## Task Contract

Required fields:

- task_id
- title
- objective
- context
- constraints
- allowed_tools
- expected_output
- risk_level

---

## Plan Contract

Planner must return:

- task_summary
- assumptions
- execution_steps
- required_tools
- expected_artifacts
- risks
- escalation_needed

---

## Execution Contract

Executor must return:

- actions_taken
- tools_used
- artifacts_created
- errors
- deviations_from_plan
- completion_status

---

## Verification Contract

Verifier must return:

- verdict
- issues_found
- policy_violations
- quality_assessment
- recommended_next_step

---

## Success Criteria

V1 is considered working when:

- the system accepts structured tasks
- each agent returns structured output
- executor uses only approved tools
- verifier returns clear verdicts
- run artifacts are saved
- runs can be reviewed afterward

---

## Run Artifacts

Each run must save:

- task input
- plan output
- execution output
- verification output
- final summary
- trace logs
