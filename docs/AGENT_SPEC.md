# Revenue Recovery Orchestrator — Agentic Intelligence Specification

> **Companion documents:** `PROJECT.md`, `TECHNICAL_SPEC.md`, `DATA_SPEC.md`  
> **Purpose:** Define how the agentic intelligence layer reasons, orchestrates decisions, uses tools, respects guardrails, and learns from outcomes.

---

# Table of Contents

1. Purpose
2. Core Agent Philosophy
3. What Makes This System Agentic
4. Agentic System Overview
5. Intelligence Responsibilities
6. What Is Not an Agent Responsibility
7. Agent Architecture
8. Why Not Use Multiple Independent Agents
9. Recommended LangGraph Design
10. End-to-End Workflow
11. Agent State
12. State Contracts
13. Node Specifications
14. Diagnostic Node
15. Prediction Context Node
16. Revenue Assessment Node
17. Candidate Action Generator
18. Churn and Customer Value Reasoning
19. Decision Node
20. Guardrail Node
21. Tool Execution Node
22. Outcome Monitor
23. Retry and Escalation Logic
24. Stop Conditions
25. Action Universe
26. Action Compatibility Rules
27. Tool Specifications
28. LLM Responsibilities
29. Structured Outputs
30. Prompting Strategy
31. Guardrail Architecture
32. Human Escalation
33. Memory and Learning
34. Outcome Feedback Loop
35. Batch Processing Strategy
36. Failure Handling
37. Auditability
38. Example Workflow
39. LangGraph Pseudocode
40. Testing Strategy
41. MVP vs Future Agent Capabilities
42. Acceptance Criteria
43. Final Agentic Principle

---

# 1. Purpose

The Revenue Recovery Orchestrator is not intended to be a chatbot that simply suggests what a merchant should do.

Its intelligence layer must behave like a bounded decision system:

```text
UNDERSTAND EVENT
      ↓
GATHER CONTEXT
      ↓
INTERPRET PREDICTIONS
      ↓
GENERATE VALID OPTIONS
      ↓
SELECT BEST ACTION
      ↓
CHECK POLICY
      ↓
EXECUTE TOOL
      ↓
OBSERVE OUTCOME
      ↓
DECIDE NEXT STEP
```

This document defines that intelligence loop.

The agentic layer sits on top of deterministic data and ML systems. It does not replace them.

---

# 2. Core Agent Philosophy

The project follows one fundamental rule:

> **Agents reason. Systems calculate. Guardrails control. Tools execute.**

This separation is mandatory.

## Agents should do

- interpret context
- compare valid actions
- explain trade-offs
- choose between bounded options
- decide workflow transitions

## Deterministic systems should do

- calculations
- probability inference
- priority scoring
- policy enforcement
- validation
- state updates

## Tools should do

- execute approved actions
- return structured results

The system should never depend on an LLM for something that must be numerically exact or policy-safe.

---

# 3. What Makes This System Agentic

The project is agentic because it contains a closed decision loop.

A normal ML pipeline:

```text
INPUT
 ↓
MODEL
 ↓
PREDICTION
 ↓
OUTPUT
```

This project:

```text
EVENT
 ↓
CONTEXT
 ↓
PREDICTIONS
 ↓
REASONING
 ↓
ACTION
 ↓
TOOL RESULT
 ↓
OUTCOME
 ↓
NEXT DECISION
```

The key difference is that the system can use the result of an action to determine what happens next.

The agent does not merely classify an event.

It participates in an orchestrated workflow.

---

# 4. Agentic System Overview

```text
                         REVENUE EVENT
                               │
                               ▼
                    ┌─────────────────────┐
                    │ CONTEXT ASSEMBLER   │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ DIAGNOSTIC NODE     │
                    │ What happened?      │
                    └──────────┬──────────┘
                               ▼
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
   ┌──────────────────┐               ┌──────────────────┐
   │ RECOVERY MODEL   │               │ CHURN MODEL      │
   │ P(recovery)      │               │ P(churn)         │
   └────────┬─────────┘               └────────┬─────────┘
            └─────────────────┬─────────────────┘
                              ▼
                  ┌─────────────────────┐
                  │ REVENUE RISK ENGINE │
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │ ACTION REASONING    │
                  │ Select from allowed │
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │ GUARDRAIL ENGINE    │
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │ EXECUTION TOOLS     │
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │ OUTCOME MONITOR     │
                  └──────────┬──────────┘
                             ▼
                       NEXT STEP / END
```

---

# 5. Intelligence Responsibilities

The intelligence layer answers five questions.

## Question 1 — What happened?

Example:

```text
A recurring payment of ₹1,999 failed because of insufficient funds.
This is the customer's first failure after a strong payment history.
```

## Question 2 — How valuable is intervention?

Example:

```text
Immediate revenue at risk: ₹1,999
Recovery probability: 0.74
Expected recovery value: ₹1,479
```

## Question 3 — What else is at risk?

Example:

```text
Customer churn probability: 0.42
Estimated future customer value: ₹18,000
```

## Question 4 — What should happen next?

Example:

```text
Retry later is preferred over immediate retry because the failure reason
suggests temporary insufficient funds and this is the first failed attempt.
```

## Question 5 — What happened after intervention?

Example:

```text
Retry failed.
Maximum retries not reached.
Customer has high lifetime value.
Generate payment link instead of repeating the same retry.
```

---

# 6. What Is Not an Agent Responsibility

The LLM/agent must not:

- calculate model probabilities
- calculate expected recovery value
- invent numerical metrics
- create arbitrary actions
- bypass retry limits
- override guardrails
- access undeclared tools
- mutate raw data
- decide policy thresholds
- execute unapproved external actions

The agent receives structured information and reasons within boundaries.

## Recoverability vs execution

Recoverability classification is not a second ML model. It uses existing P(recovery), ERV, status, and policy signals to decide whether an intervention is justified. Low expected value can yield **no action**. Guardrails remain the authority for closed events, cooldowns, and max attempts.

## Ask Recovery Copilot (not an executor)

The Event Detail **Ask Recovery Copilot** is a read-only explainer. One shared service answers questions for whichever `event_id` is open. It loads grounded workflow context for that event, uses Ollama when available, and falls back deterministically. It must not run the recovery graph, execute simulated tools, or modify policy.

---

# 7. Agent Architecture

The MVP should use a **graph of specialized nodes**, not a collection of independent autonomous bots talking endlessly to each other.

Conceptual architecture:

```text
                    ┌──────────────────┐
                    │ ORCHESTRATOR     │
                    │ LANGGRAPH STATE  │
                    └────────┬─────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      ▼                      ▼                      ▼
 DIAGNOSIS              DECISION                MONITOR
      │                      │                      │
      ▼                      ▼                      ▼
 Structured Context     Approved Action        Outcome
```

Some nodes may use an LLM.

Some nodes are deterministic Python.

The graph is more important than the number of "agents."

---

# 8. Why Not Use Multiple Independent Agents

A tempting architecture is:

```text
Agent A talks to Agent B
Agent B talks to Agent C
Agent C debates Agent D
```

This sounds sophisticated but creates problems:

- slower execution
- higher API cost
- difficult debugging
- unpredictable conversations
- weak auditability

For this MVP, the preferred architecture is:

```text
SPECIALIZED NODE
      ↓
STRUCTURED STATE UPDATE
      ↓
NEXT NODE
```

This is easier to:

- test
- visualize
- explain to judges
- control
- debug

The project can still be described as multi-agent or agentic if specialized reasoning responsibilities are clearly separated, but implementation should not create complexity for appearance.

---

# 9. Recommended LangGraph Design

Recommended graph nodes:

```text
START
  ↓
assemble_context
  ↓
diagnose_event
  ↓
get_predictions
  ↓
assess_revenue_risk
  ↓
generate_candidates
  ↓
select_action
  ↓
validate_action
  ↓
execute_action
  ↓
monitor_outcome
  ↓
conditional_router
  ├── success → finalize_success
  ├── retry → next_attempt
  ├── alternate_action → generate_candidates
  ├── escalate → escalate_to_human
  └── stop → finalize
```

The graph must have explicit conditional edges.

No uncontrolled loops.

---

# 10. End-to-End Workflow

## Step 1 — Receive event

Input:

```text
event_id
customer_id
amount_at_risk
failure_reason
attempt_number
```

## Step 2 — Assemble context

Fetch/build:

- customer context
- transaction history
- subscription context
- intervention history
- merchant policies

## Step 3 — Diagnose event

Produce structured diagnosis:

- event summary
- likely issue category
- relevant context
- special considerations

## Step 4 — Obtain predictions

Deterministic ML services return:

```text
recovery_probability
churn_probability
```

## Step 5 — Assess revenue risk

Deterministic engine calculates:

```text
expected_recovery_value
priority_score
priority_category
```

## Step 6 — Generate candidates

The system creates only compatible actions.

Example:

```text
retry_later
payment_link
payment_method_update
```

## Step 7 — Select action

Reasoning layer compares candidates.

## Step 8 — Guardrail validation

Action may be:

- allowed
- blocked
- modified
- escalated

## Step 9 — Execute tool

Simulated tool performs action.

## Step 10 — Monitor outcome

Observe/simulate result.

## Step 11 — Decide next state

Possible transitions:

```text
SUCCESS
RETRY
ALTERNATIVE_ACTION
ESCALATE
STOP
```

---

# 11. Agent State

The LangGraph state is the single source of truth during a workflow.

Conceptual structure:

```text
WorkflowState
│
├── workflow_id
├── event
├── customer_context
├── merchant_context
├── transaction_context
├── subscription_context
├── intervention_history
│
├── diagnosis
├── recovery_prediction
├── churn_prediction
├── risk_assessment
│
├── candidate_actions
├── selected_action
├── decision_rationale
│
├── guardrail_result
├── action_history
├── latest_tool_result
│
├── outcome
├── next_step
│
├── attempt_count
├── status
│
└── audit_entries
```

All nodes should update only relevant fields.

Avoid uncontrolled mutation.

---

# 12. State Contracts

Every state field should have a clear owner.

| State Field | Primary Producer |
|---|---|
| event | Context assembler |
| customer_context | Context assembler |
| diagnosis | Diagnostic node |
| recovery_prediction | ML service |
| churn_prediction | ML service |
| risk_assessment | Revenue Risk Engine |
| candidate_actions | Candidate generator |
| selected_action | Decision node |
| guardrail_result | Guardrail Engine |
| latest_tool_result | Tool node |
| outcome | Outcome Monitor |
| audit_entries | Audit service |

This makes debugging much easier.

---

# 13. Node Specifications

The graph contains the following conceptual nodes.

## Deterministic nodes

- assemble_context
- get_predictions
- assess_revenue_risk
- generate_candidates
- validate_action
- execute_action
- monitor_outcome
- finalize

## Reasoning nodes

- diagnose_event
- select_action

The architecture intentionally limits LLM-dependent nodes.

---

# 14. Diagnostic Node

## Purpose

Convert raw structured context into a concise operational diagnosis.

## Inputs

- event
- customer context
- transaction history summary
- intervention history

## Output

Structured diagnosis:

```json
{
  "event_summary": "...",
  "issue_category": "...",
  "key_factors": [
    "...",
    "..."
  ],
  "risk_notes": [
    "..."
  ]
}
```

## Example

Input:

```text
Amount: ₹4,999
Failure: card_expired
Attempt: 1
Customer tenure: 420 days
Payment success rate: 94%
```

Output:

```text
The payment failure is likely caused by an outdated payment instrument rather
than poor customer intent. Historical payment reliability is strong. Repeating
the same payment method is unlikely to be optimal.
```

The output should be explanation, not invented probability.

---

# 15. Prediction Context Node

This is primarily deterministic.

The node calls:

```text
RecoveryModel.predict_proba()
```

and:

```text
ChurnModel.predict_proba()
```

Outputs:

```json
{
  "recovery_probability": 0.74,
  "churn_probability": 0.31
}
```

The reasoning agent may interpret these values but must not alter them.

---

# 16. Revenue Assessment Node

Deterministic calculation.

Inputs:

- amount at risk
- recovery probability
- churn probability
- customer value
- urgency
- intervention cost estimates

Outputs:

```text
expected_recovery_value
priority_score
priority_category
```

Example:

```text
Amount at risk = ₹10,000
Recovery probability = 0.70

Expected recovery value = ₹7,000
```

This node should remain completely independent of LLM calls.

---

# 17. Candidate Action Generator

The candidate generator produces valid actions before reasoning.

Example:

Event:

```text
failure_reason = card_expired
attempt_number = 1
```

Candidate generation may produce:

```text
payment_method_update
payment_link
email
whatsapp
```

and exclude:

```text
retry_now
```

if retrying the same expired card is incompatible.

Candidate generation can combine:

- event compatibility rules
- merchant allowed actions
- guardrail preconditions
- previous action history

The LLM should select among candidates rather than inventing actions.

---

# 18. Churn and Customer Value Reasoning

Churn is not a separate parallel product.

It enriches revenue recovery decisions.

Example:

### Customer A

```text
Amount at risk: ₹2,000
Recovery probability: 0.70
Churn probability: 0.05
LTV: ₹4,000
```

Aggressive retention intervention is probably unnecessary.

### Customer B

```text
Amount at risk: ₹2,000
Recovery probability: 0.55
Churn probability: 0.72
LTV: ₹80,000
```

The system should recognize that the immediate failed payment is not the entire problem.

The action strategy may shift toward lower-friction retention.

This is one of the project's differentiating intelligence layers.

---

# 19. Decision Node

## Purpose

Choose the best action from the valid candidate set.

## Inputs

- diagnosis
- recovery probability
- churn probability
- customer value
- risk assessment
- candidate actions
- action history

## Output

Structured decision:

```json
{
  "selected_action": "retry_later",
  "reasoning": "The failure appears temporary...",
  "expected_goal": "Recover immediate payment with low customer friction",
  "alternative_considered": "payment_link"
}
```

## Important constraint

The selected action must exactly match one candidate action.

No new action can be invented.

---

# 20. Guardrail Node

The Guardrail Node is not an LLM.

Input:

```text
selected_action
+
event
+
merchant policy
+
history
```

Output:

```text
ALLOW
BLOCK
MODIFY
ESCALATE
```

Example:

```text
Selected action: retry_later
Previous retries: 3
Merchant max retries: 3

Result: BLOCK
```

Possible modification:

```text
Selected: retry_now
Cooldown violation

Modified:
retry_later at next permitted window
```

All rule triggers must be logged.

---

# 21. Tool Execution Node

The Tool Execution Node maps the approved action to a deterministic tool.

Example:

```text
selected_action
      ↓
Tool Registry
      ↓
retry_later()
      ↓
ActionResult
```

Every execution returns a common result structure.

```json
{
  "action_id": "ACT_001",
  "action_type": "retry_later",
  "status": "executed",
  "timestamp": "...",
  "metadata": {}
}
```

The tool node must not decide which tool to execute.

It only executes the already approved action.

---

# 22. Outcome Monitor

The Outcome Monitor consumes:

- action
- tool result
- event context
- model predictions
- simulation rules

Outputs:

```text
recovered
failed
ignored
pending
retained
churned
escalated
stopped
```

Example:

```text
Action: retry_later
Outcome: failed
```

The workflow then evaluates:

```text
Can retry?
Try alternative?
Escalate?
Stop?
```

---

# 23. Retry and Escalation Logic

The workflow must avoid repetitive loops.

Example state machine:

```text
ACTION
  ↓
OUTCOME
  ↓
SUCCESS?
 ├── YES → END
 │
 └── NO
      ↓
ATTEMPTS < LIMIT?
 ├── YES → ALTERNATIVE ACTION
 │
 └── NO
      ↓
HIGH VALUE / HIGH RISK?
 ├── YES → ESCALATE
 └── NO → STOP
```

Important:

A retry does not always mean repeating the exact same action.

The system should prefer action diversity where appropriate.

---

# 24. Stop Conditions

Every workflow must terminate.

Stop conditions include:

```text
payment recovered
```

```text
maximum attempts reached
```

```text
expected value below threshold
```

```text
customer friction limit reached
```

```text
human escalation required
```

```text
no valid actions remaining
```

```text
fatal tool error
```

The graph must never contain an unbounded cycle.

---

# 25. Action Universe

Initial approved action set:

| Action | Description |
|---|---|
| retry_now | Retry payment immediately |
| retry_later | Schedule delayed retry |
| generate_payment_link | Create alternate payment path |
| send_email | Simulated email outreach |
| send_whatsapp | Simulated WhatsApp outreach |
| payment_method_update | Request updated payment method |
| retention_offer | Offer approved retention incentive |
| escalate_to_human | Human review |
| stop_recovery | End workflow |

The action universe is intentionally finite.

Future actions may be added through explicit configuration.

---

# 26. Action Compatibility Rules

Candidate generation should apply basic compatibility logic.

## network_error

Likely candidates:

```text
retry_now
retry_later
```

## payment_timeout

Likely candidates:

```text
retry_now
retry_later
payment_link
```

## insufficient_funds

Likely candidates:

```text
retry_later
payment_link
```

## card_expired

Likely candidates:

```text
payment_method_update
payment_link
email
whatsapp
```

## repeated_payment_failure

Likely candidates:

```text
payment_link
payment_method_update
escalate_to_human
stop_recovery
```

These are not rigid production rules. They are bounded candidate-generation heuristics for the MVP.

---

# 27. Tool Specifications

## retry_payment

Input:

```text
event_id
attempt_number
```

Output:

```text
status
attempt_id
```

## schedule_retry

Input:

```text
event_id
scheduled_time
```

Output:

```text
schedule_id
status
```

## generate_payment_link

Input:

```text
event_id
amount
```

Output:

```text
link_id
status
```

No real public payment URL is required for MVP.

## send_email

Input:

```text
customer_id
template_type
```

Output:

```text
message_id
status
```

Simulated.

## send_whatsapp

Same pattern as email.

Simulated.

## payment_method_update

Records a request for an updated payment instrument.

## retention_offer

Input:

```text
customer_id
offer_type
```

Guardrails must constrain offer eligibility.

## escalate_to_human

Creates a simulated review task.

## stop_recovery

Marks workflow terminal.

---

# 28. LLM Responsibilities

The LLM should be used sparingly.

Recommended uses:

### 1. Event diagnosis

Transform structured signals into understandable operational interpretation.

### 2. Candidate comparison

Compare approved actions using context.

### 3. Decision explanation

Generate human-readable reasoning.

The LLM should receive compact context.

Avoid sending full transaction histories when summary statistics are sufficient.

---

# 29. Structured Outputs

LLM outputs must be schema-constrained.

Never rely on:

```text
plain natural language parsing
```

Preferred conceptual output:

```json
{
  "issue_category": "temporary_payment_failure",
  "key_factors": [
    "high historical payment success",
    "first failed attempt"
  ],
  "recommended_action": "retry_later",
  "reason": "...",
  "confidence_note": "..."
}
```

After parsing:

```text
Validate against Pydantic schema
        ↓
Validate action exists in candidates
        ↓
Pass to Guardrail Engine
```

Malformed output should trigger retry/fallback logic.

---

# 30. Prompting Strategy

Prompts should be role-specific and narrow.

## Diagnostic prompt principles

Tell the model:

- analyze only supplied data
- do not invent facts
- do not generate probabilities
- identify relevant signals
- return structured output

## Decision prompt principles

Tell the model:

- choose only from supplied candidate actions
- consider recovery and churn context
- minimize unnecessary customer friction
- provide concise reasoning
- return structured output

The model should not be given broad instructions like:

```text
Do whatever is best for the merchant.
```

Bounded instructions are essential.

---

# 31. Guardrail Architecture

Guardrails are applied in multiple layers.

## Layer 1 — Candidate filtering

Remove obviously invalid actions before LLM reasoning.

## Layer 2 — Post-decision validation

Check selected action against:

- attempt limits
- contact limits
- cooldowns
- merchant policy
- escalation thresholds

## Layer 3 — Tool validation

Tools validate their own input contracts.

Architecture:

```text
Candidate Generator
       ↓
Valid Candidate Set
       ↓
LLM Decision
       ↓
Guardrail Engine
       ↓
Approved Action
       ↓
Tool Input Validation
       ↓
Execution
```

Defense in depth is preferred.

---

# 32. Human Escalation

Escalation is a first-class workflow outcome.

Trigger examples:

- high-value event
- repeated failures
- no valid automated action
- high customer value + high churn
- policy conflict
- tool failures

Escalation result:

```json
{
  "status": "escalated",
  "reason": "Repeated failures with high customer lifetime value",
  "recommended_context": "..."
}
```

For MVP, escalation can simply appear as a simulated task in the dashboard.

---

# 33. Memory and Learning

The MVP should not claim online reinforcement learning.

That would add unnecessary complexity.

Instead, use two forms of memory.

## Short-term workflow memory

Stored in LangGraph state:

```text
actions attempted
tool results
attempt count
current status
```

## Historical operational memory

Stored in:

```text
intervention_history.csv
audit_logs.jsonl
```

This allows future decisions to consider:

- previous actions
- previous outcomes
- action effectiveness

---

# 34. Outcome Feedback Loop

The conceptual learning loop is:

```text
EVENT
 ↓
PREDICTION
 ↓
ACTION
 ↓
OUTCOME
 ↓
LOG OUTCOME
 ↓
HISTORICAL DATASET GROWS
 ↓
FUTURE MODEL RETRAINING
```

For the hackathon MVP:

- outcomes are recorded
- action effectiveness is measurable
- retraining is conceptually supported

Automatic live model retraining is not required.

This distinction is important.

Do not falsely claim:

```text
The model learns instantly after every event.
```

Instead say:

```text
The system records intervention outcomes to create a feedback dataset for future model recalibration and retraining.
```

---

# 35. Batch Processing Strategy

Agent workflows are expensive compared with deterministic ML inference.

Therefore:

```text
ALL EVENTS
    ↓
Batch feature engineering
    ↓
Batch ML predictions
    ↓
Batch risk scoring
    ↓
Rank opportunities
    ↓
Top / selected events
    ↓
Deep agent workflow
```

This avoids:

```text
10,000 events
×
10,000 LLM calls
```

For dashboard demos:

- process all events deterministically
- run agent workflows for selected/high-priority events
- allow user to inspect any individual event on demand

This is both technically efficient and easier to explain.

---

# 36. Failure Handling

## LLM unavailable

Fallback:

```text
Deterministic action ranking
```

Example priority order can be based on compatibility and historical action effectiveness.

## Invalid LLM output

```text
Retry structured generation once
↓
Fallback to deterministic selector
```

## Tool failure

```text
Record error
↓
Check alternate action
↓
Escalate or stop
```

## Missing context

Proceed only if minimum required fields exist.

Otherwise:

```text
status = insufficient_context
```

and optionally escalate.

The system should degrade gracefully.

---

# 37. Auditability

Every important agentic step should be inspectable.

Example audit timeline:

```text
10:00:01
Context assembled

10:00:02
Recovery probability generated: 0.74

10:00:02
Churn probability generated: 0.31

10:00:03
Expected recovery value calculated: ₹1,479

10:00:04
Candidates generated:
retry_later, payment_link

10:00:05
Action selected:
retry_later

10:00:05
Guardrail:
ALLOW

10:00:06
Tool executed

10:00:08
Outcome:
recovered
```

The dashboard should expose this timeline.

This is important for demonstrating that the AI system is explainable.

---

# 38. Example Workflow

## Scenario

Merchant:

```text
SaaS subscription business
```

Customer:

```text
Customer tenure: 18 months
Historical payment success: 93%
Customer LTV: ₹45,000
Engagement: high
```

Event:

```text
Monthly subscription: ₹2,499
Failure reason: insufficient_funds
Attempt: 1
```

### Step 1 — Diagnosis

```text
The customer has historically strong payment behavior.
The failure appears potentially temporary.
```

### Step 2 — Predictions

```text
Recovery probability: 0.78
Churn probability: 0.18
```

### Step 3 — Risk assessment

```text
Immediate revenue: ₹2,499
Expected recovery value: ₹1,949
Priority: HIGH
```

### Step 4 — Candidates

```text
retry_later
payment_link
```

### Step 5 — Decision

```text
retry_later
```

Reason:

```text
Insufficient funds may be temporary and a delayed retry has lower customer friction than immediate outreach.
```

### Step 6 — Guardrail

```text
ALLOW
```

### Step 7 — Tool

```text
schedule_retry()
```

### Step 8 — Outcome

```text
Payment recovered
```

### Step 9 — Final result

```text
Recovered amount: ₹2,499
Workflow status: SUCCESS
```

---

# 39. LangGraph Pseudocode

Conceptual pseudocode only:

```python
graph = StateGraph(WorkflowState)

graph.add_node("assemble_context", assemble_context)
graph.add_node("diagnose_event", diagnose_event)
graph.add_node("get_predictions", get_predictions)
graph.add_node("assess_risk", assess_risk)
graph.add_node("generate_candidates", generate_candidates)
graph.add_node("select_action", select_action)
graph.add_node("validate_action", validate_action)
graph.add_node("execute_action", execute_action)
graph.add_node("monitor_outcome", monitor_outcome)
graph.add_node("finalize", finalize)

graph.add_edge(START, "assemble_context")
graph.add_edge("assemble_context", "diagnose_event")
graph.add_edge("diagnose_event", "get_predictions")
graph.add_edge("get_predictions", "assess_risk")
graph.add_edge("assess_risk", "generate_candidates")
graph.add_edge("generate_candidates", "select_action")
graph.add_edge("select_action", "validate_action")

graph.add_conditional_edges(
    "validate_action",
    route_after_validation
)

graph.add_edge("execute_action", "monitor_outcome")

graph.add_conditional_edges(
    "monitor_outcome",
    route_after_outcome
)
```

Actual implementation should use typed state and explicit conditional routes.

---

# 40. Testing Strategy

## Unit tests

### Diagnostic node

- valid context
- missing optional context
- structured output

### Candidate generator

- compatible actions
- incompatible actions excluded

### Decision node

- selected action belongs to candidate set

### Guardrails

- retry limits
- cooldowns
- escalation thresholds

### Routing

- success route
- retry route
- stop route
- escalation route

## Integration tests

```text
Event
 ↓
Context
 ↓
Predictions
 ↓
Risk
 ↓
Decision
 ↓
Guardrail
 ↓
Tool
 ↓
Outcome
```

## Mocking

LLM calls should be mockable.

The deterministic fallback path must also be tested.

---

# 41. MVP vs Future Agent Capabilities

## MVP

- structured context
- event diagnosis
- bounded action selection
- deterministic guardrails
- simulated tools
- outcome monitoring
- audit trail
- historical outcome logging

## Future

Potential extensions:

- real payment integrations
- real communication APIs
- action effectiveness models
- contextual bandits
- automated policy tuning
- human approval workflows
- persistent agent memory
- multi-merchant personalization

Do not build future architecture prematurely.

---

# 42. Acceptance Criteria

The agent layer is complete when:

### State

- [ ] Typed workflow state exists
- [ ] Every important decision is represented in state

### Graph

- [ ] LangGraph workflow executes
- [ ] Conditional routing works
- [ ] All loops are bounded
- [ ] Terminal states exist

### Intelligence

- [ ] Event diagnosis works
- [ ] Recovery/churn predictions are consumed
- [ ] Candidate actions are generated
- [ ] Action selection is bounded

### Safety

- [ ] Agent cannot invent actions
- [ ] Guardrails can block decisions
- [ ] Tools validate inputs

### Outcomes

- [ ] Simulated action result is generated
- [ ] Outcome updates workflow
- [ ] Success/failure routing works

### Auditability

- [ ] Every major step is logged
- [ ] Dashboard can reconstruct decision timeline

### Reliability

- [ ] LLM fallback exists
- [ ] Invalid output is handled
- [ ] Tool failures are handled

---

# 43. Final Agentic Principle

The intelligence of this project should not come from saying:

> "We have many AI agents."

It should come from demonstrating a credible autonomous decision loop:

```text
UNDERSTAND
    ↓
PREDICT
    ↓
PRIORITIZE
    ↓
REASON
    ↓
DECIDE
    ↓
VALIDATE
    ↓
ACT
    ↓
OBSERVE
    ↓
ADAPT
```

The strongest implementation is therefore not the one with the most agents.

It is the one where every decision has:

- a clear input
- a defined owner
- bounded choices
- policy validation
- observable outcomes
- an auditable trail

> **The Revenue Recovery Orchestrator should behave less like a chatbot and more like an intelligent operational system with controlled autonomy.**
