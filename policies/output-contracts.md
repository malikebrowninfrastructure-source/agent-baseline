# Output Contracts

## Purpose
Define the required structured outputs for the baseline workflow.

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

## Plan Contract
Planner must return:
- task_summary
- assumptions
- execution_steps
- required_tools
- expected_artifacts
- risks
- escalation_needed

Rules:
- assumptions must be explicit
- execution steps must be ordered and concrete
- required tools must align with policy
- expected artifacts must be identifiable
- risks must be meaningful, not generic filler

## Execution Contract
Executor must return:
- actions_taken
- tools_used
- artifacts_created
- errors
- deviations_from_plan
- completion_status

Rules:
- actions must reflect real work performed
- tools_used must reflect actual tool usage
- errors must be explicit
- deviations must be documented
- completion_status must be honest

## Verification Contract
Verifier must return:
- verdict
- issues_found
- policy_violations
- quality_assessment
- recommended_next_step

Rules:
- verdict must be explicit
- issues_found must identify concrete deficiencies
- policy_violations must be listed when present
- quality_assessment must be reviewable
- recommended_next_step must be actionable

## Finalization Contract
Orchestrator must return:
- final_status
- summary_of_run
- escalation_note_if_any
- artifact_index
- trace_reference

Rules:
- final_status must be one of: pass, fail, retry, escalate
- summary_of_run must reflect actual prior outputs
- artifact_index must point to saved outputs
- trace_reference must identify the run trace
