# Revenue Recovery Orchestrator — Technical Specification

> **Companion document:** `PROJECT.md`  
> **Purpose:** Define how RevenueOS is structured and implemented.

---

# Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Technical Philosophy](#2-technical-philosophy)
3. [MVP Architecture](#3-mvp-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Repository Structure](#5-repository-structure)
6. [System Boundaries](#6-system-boundaries)
7. [File-First Data Architecture](#7-file-first-data-architecture)
8. [Data Ingestion and Normalization](#8-data-ingestion-and-normalization)
9. [Internal Data Contracts](#9-internal-data-contracts)
10. [Feature Engineering](#10-feature-engineering)
11. [Machine Learning Architecture](#11-machine-learning-architecture)
12. [Revenue Risk Engine](#12-revenue-risk-engine)
13. [Agent Architecture](#13-agent-architecture)
14. [LangGraph Workflow](#14-langgraph-workflow)
15. [Agent State](#15-agent-state)
16. [LLM vs ML vs Deterministic Code](#16-llm-vs-ml-vs-deterministic-code)
17. [Action Selection](#17-action-selection)
18. [Tool Architecture](#18-tool-architecture)
19. [Guardrail Engine](#19-guardrail-engine)
20. [Outcome Simulation and Monitoring](#20-outcome-simulation-and-monitoring)
21. [Audit Architecture](#21-audit-architecture)
22. [Persistence Strategy](#22-persistence-strategy)
23. [FastAPI Architecture](#23-fastapi-architecture)
24. [Batch and Single Event Processing](#24-batch-and-single-event-processing)
25. [Frontend-Backend Contract](#25-frontend-backend-contract)
26. [Error Handling and Fallbacks](#26-error-handling-and-fallbacks)
27. [Configuration](#27-configuration)
28. [Logging and Observability](#28-logging-and-observability)
29. [Testing Strategy](#29-testing-strategy)
30. [Performance Principles](#30-performance-principles)
31. [Development Rules](#31-development-rules)
32. [Implementation Sequence](#32-implementation-sequence)
33. [Technical Decisions and Deferred Items](#33-technical-decisions-and-deferred-items)

---

# 1. Purpose and Scope

`PROJECT.md` defines the product vision, problem, users, and high-level architecture.

This document defines the technical implementation strategy.

The project is a **hackathon prototype**, not a production banking platform. The architecture must therefore maximize:

- implementation speed
- clarity
- reliability
- demonstrability
- explainability
- modularity

It must minimize:

- infrastructure overhead
- unnecessary backend complexity
- operational dependencies
- premature scalability work

The central implementation goal is to build a system that can:

1. ingest revenue-risk data
2. normalize it into a common representation
3. generate relevant features
4. estimate recovery probability
5. estimate churn/customer value risk
6. calculate expected recovery value
7. prioritize opportunities
8. reason about the event using bounded agents
9. select an approved recovery action
10. validate the action against guardrails
11. execute a simulated action
12. monitor/simulate the outcome
13. record actual recovered value
14. expose results through a merchant dashboard
15. maintain a complete audit trail

---

# 2. Technical Philosophy

## 2.1 File-first, not database-first

The MVP does **not** require PostgreSQL.

The primary workflow begins with:

```text
CSV / Excel
    ↓
Pandas
    ↓
Normalized Internal Data
    ↓
ML + Risk Engine
    ↓
Agent Workflow
    ↓
Results
```

A relational database can be introduced later if persistence/query complexity genuinely requires it.

For the MVP:

- CSV is the main tabular input format
- XLSX is supported for merchant convenience
- JSON/JSONL stores structured decisions and audit logs
- Parquet is optional for larger processed datasets

## 2.2 Thin backend

FastAPI exists primarily to:

- receive files
- trigger analysis
- expose results
- coordinate the Python engine

FastAPI is **not** intended to become a heavy enterprise backend.

## 2.3 AI is not everything

The implementation follows this strict separation:

| Responsibility | Technology |
|---|---|
| Data processing | Pandas / NumPy |
| Numerical prediction | ML models |
| Risk calculations | Deterministic Python |
| Reasoning and interpretation | LLM |
| Workflow orchestration | LangGraph |
| Policy enforcement | Deterministic Python |
| Tool execution | Python services/functions |
| Persistence | Files |
| Visualization | React |

## 2.4 Bounded autonomy

Agents may reason and choose between allowed options.

Agents may not:

- invent new actions
- bypass policy
- override deterministic guardrails
- invent numerical probabilities
- directly mutate raw source data
- execute arbitrary code

---

# 3. MVP Architecture

```text
                         ┌──────────────────────┐
                         │      FRONTEND        │
                         │ React + TypeScript   │
                         └──────────┬───────────┘
                                    │ REST
                                    ▼
                         ┌──────────────────────┐
                         │       FASTAPI        │
                         │ Thin API Layer       │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌────────────────┐    ┌─────────────────┐   ┌─────────────────┐
     │ File Ingestion │    │ Recovery Engine │   │ Results Service │
     └───────┬────────┘    └────────┬────────┘   └────────┬────────┘
             │                      │                     │
             ▼                      ▼                     ▼
      CSV / XLSX            ML + LangGraph         JSON / CSV / JSONL
             │                      │
             ▼                      ▼
       Normalization        Revenue Intelligence
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Revenue Risk Engine  │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Agent Orchestrator   │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Guardrail Engine     │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Simulated Tools      │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Outcome Monitor      │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Audit + Analytics    │
                         └──────────────────────┘
```

---

# 4. Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
| React | Component-based UI |
| TypeScript | Type safety |
| Vite | Fast development/build tooling |
| Tailwind CSS | Rapid UI development |
| Recharts | Analytics visualization |
| Lucide React | Consistent iconography |

## Backend

| Technology | Purpose |
|---|---|
| Python | Core intelligence layer |
| FastAPI | Thin REST API |
| Uvicorn | ASGI server |
| Pydantic | Request/response validation |

## Data

| Technology | Purpose |
|---|---|
| Pandas | Tabular processing |
| NumPy | Numerical operations |
| CSV | Primary input/output |
| XLSX | Merchant upload convenience |
| JSON | Structured workflow results |
| JSONL | Append-only audit logs |
| Parquet | Optional efficient processed storage |

## Machine Learning

| Technology | Purpose |
|---|---|
| Scikit-learn | Baselines/preprocessing/evaluation |
| XGBoost | Strong tabular model candidate |
| Joblib | Model serialization |

## Agentic AI

| Technology | Purpose |
|---|---|
| LangGraph | Explicit workflow/state transitions |
| LLM API | Structured reasoning and explanation |

## Testing

| Technology | Purpose |
|---|---|
| Pytest | Backend and engine testing |

---

# 5. Repository Structure

```text
project-root/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── utils/
│   │   └── App.tsx
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── constants.py
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── data/
│   │   │   ├── loaders/
│   │   │   ├── validators/
│   │   │   ├── transformers/
│   │   │   └── feature_engineering/
│   │   ├── ml/
│   │   │   ├── training/
│   │   │   ├── inference/
│   │   │   ├── models/
│   │   │   └── features/
│   │   ├── risk/
│   │   ├── agents/
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   ├── nodes/
│   │   │   └── prompts/
│   │   ├── guardrails/
│   │   ├── tools/
│   │   ├── monitoring/
│   │   └── simulation/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── data/
│   ├── input/
│   ├── synthetic/
│   ├── processed/
│   ├── outputs/
│   └── models/
│
├── docs/
│   ├── PROJECT.md
│   └── TECHNICAL_SPEC.md
│
├── scripts/
├── .env.example
├── README.md
└── .gitignore
```

### Folder responsibility

- `frontend`: merchant-facing application
- `api`: HTTP boundary only
- `schemas`: Pydantic contracts
- `services`: application coordination
- `data`: ingestion and transformation
- `ml`: training and inference
- `risk`: deterministic business scoring
- `agents`: LangGraph workflow
- `guardrails`: policy checks
- `tools`: controlled action execution
- `monitoring`: outcomes and audit generation
- `simulation`: synthetic data and simulated outcomes

---

# 6. System Boundaries

## Frontend responsibilities

The frontend may:

- upload files
- trigger analysis
- display metrics
- display opportunities
- display agent decisions
- display audit timelines

The frontend must not:

- run ML inference
- contain recovery scoring logic
- execute tools directly
- implement guardrails independently

## FastAPI responsibilities

FastAPI should:

- validate requests
- coordinate services
- invoke the recovery pipeline
- return typed responses

It should avoid containing deep business logic directly in route handlers.

## Engine responsibilities

The Python intelligence layer owns:

- feature engineering
- ML inference
- risk scoring
- workflow execution
- guardrails
- tools
- outcomes

---

# 7. File-First Data Architecture

```text
data/
├── input/
│   └── Original merchant uploads
│
├── synthetic/
│   └── Generated demo datasets
│
├── processed/
│   └── Normalized and feature-engineered datasets
│
├── outputs/
│   ├── recovery_results.csv
│   ├── decisions.json
│   ├── audit_logs.jsonl
│   ├── analytics_summary.json
│   └── simulation_runs/
│
└── models/
    ├── recovery_model.joblib
    ├── churn_model.joblib
    └── preprocessing artifacts
```

### Format rules

**CSV**
- tabular input
- tabular batch outputs

**JSON**
- structured decisions
- workflow results
- analytics summaries

**JSONL**
- append-only event/audit records

**Parquet**
- optional only when processed datasets become large

Raw files must never be mutated.

---

# 8. Data Ingestion and Normalization

## Pipeline

```text
Upload
  ↓
File Validation
  ↓
Load into DataFrame
  ↓
Column Inspection
  ↓
Column Mapping
  ↓
Schema Validation
  ↓
Cleaning
  ↓
Canonical Normalization
  ↓
Internal Revenue Events
```

## Supported formats

Initial MVP:

- `.csv`
- `.xlsx`

## Column mapping

Merchant data may use different names.

Examples:

```text
amount
payment_amount
transaction_value
order_value
```

may map to:

```text
amount
```

The mapping layer should be explicit and configurable.

## Validation

The system should validate:

- file extension
- readable file
- non-empty dataset
- required columns
- numeric amount
- valid timestamps where present
- supported event types

Errors must be descriptive.

---

# 9. Internal Data Contracts

The project should use typed Pydantic models conceptually equivalent to the following.

## RevenueEvent

Represents a normalized revenue-risk event.

Key fields:

- event_id
- event_type
- merchant_id
- customer_id
- amount
- timestamp
- failure_reason
- payment_method
- attempt_number
- metadata

Producer: normalization layer  
Consumer: features, ML, risk engine, agents

## CustomerContext

Contains relevant customer history.

Key fields:

- customer_id
- tenure_days
- payment_success_rate
- previous_failures
- previous_recovery_success
- engagement_score
- activity_trend
- estimated_lifetime_value

## MerchantContext

Contains merchant policy/business context.

Key fields:

- merchant_id
- merchant_type
- retry_limit
- contact_limit
- escalation_threshold
- approved_actions

## RecoveryPrediction

- probability
- model_version
- confidence metadata

## ChurnPrediction

- probability
- estimated_customer_value
- future_revenue_at_risk

## RiskAssessment

- expected_recovery_value
- priority_score
- priority_category
- reasoning factors

## AgentDecision

- candidate_actions
- selected_action
- rationale
- confidence/decision metadata

## GuardrailResult

- status: ALLOW/BLOCK/MODIFY/ESCALATE
- triggered_rules
- final_action

## ActionRequest

- action_type
- event_id
- customer context
- parameters

## ActionResult

- action_id
- status
- timestamp
- metadata

## RecoveryOutcome

- outcome_type
- amount_recovered
- time_to_recovery
- status

## AuditEntry

- timestamp
- workflow_id
- event_id
- component
- step
- decision
- result

---

# 10. Feature Engineering

Feature engineering must be reusable between training and inference.

## Transaction features

- amount
- event_type
- payment_method
- failure_reason
- attempt_number
- time_since_event

## Customer features

- tenure_days
- historical_payment_success_rate
- previous_failures
- previous_recovery_success
- engagement_score
- activity_trend

## Subscription features

- subscription_age
- recurring_amount
- payment_frequency
- failed_cycles

## Time features

- hour
- day_of_week
- days_since_last_successful_payment

## Rules

- no feature leakage
- same preprocessing for train/inference
- missing value strategy must be explicit
- categorical encoding must be serialized with the pipeline

Preferred approach:

```text
Raw Data
  ↓
Feature Builder
  ↓
Preprocessing Pipeline
  ↓
Model
```

---

# 11. Machine Learning Architecture

Two separate prediction problems are required.

## 11.1 Recovery Probability Model

Predict:

```text
P(recovery | event, customer, context)
```

### Candidate features

- event type
- amount
- failure reason
- payment method
- customer tenure
- payment history
- previous attempts
- engagement
- time features

### Target

Binary:

```text
1 = recovered
0 = not recovered
```

### Development strategy

1. Logistic Regression baseline
2. XGBoost candidate
3. Compare evaluation results
4. Select best model for MVP

Do not assume XGBoost automatically wins.

### Evaluation

- ROC-AUC
- Precision
- Recall
- F1
- PR-AUC where useful

Because output probabilities feed downstream scoring, calibration should be evaluated.

---

## 11.2 Churn Probability Model

Predict:

```text
P(customer churns | behavior and payment context)
```

### Candidate features

- tenure
- payment failures
- delayed payments
- activity trend
- engagement
- subscription history
- prior recovery history

### Outputs

- churn_probability
- estimated customer value
- future revenue at risk

### Evaluation

- ROC-AUC
- Precision
- Recall
- F1

---

# 12. Revenue Risk Engine

The Revenue Risk Engine is deterministic Python logic.

It does not require an LLM.

## Primary calculation

```text
Expected Recovery Value
=
Revenue At Risk × Recovery Probability
```

Example:

```text
₹10,000 × 0.70 = ₹7,000
```

## Priority scoring

The conceptual prioritization function considers:

```text
Expected Recovery Value
+ Customer Value Impact
+ Urgency
- Intervention Cost
- Friction Penalty
- Policy Penalty
```

Weights must not be scattered as magic numbers.

They should live in a centralized configuration object.

## Output

Each event receives:

- expected_recovery_value
- priority_score
- priority_category

Categories:

- CRITICAL
- HIGH
- MEDIUM
- LOW

The engine must be independently unit-testable.

---

# 13. Agent Architecture

The system uses agents for bounded reasoning.

Recommended conceptual responsibilities:

## Diagnostic Agent

Answers:

- what happened?
- what likely caused the failure?
- what context matters?
- is the case straightforward or unusual?

## Recovery Decision Agent

Answers:

- which approved recovery action is most suitable?

## Churn/Value Reasoning Component

Interprets:

- churn prediction
- customer value
- future revenue risk

## Orchestrator

Coordinates all outputs and workflow transitions.

Important: these do not need to be implemented as four independent LLM calls.

The architecture should prioritize simplicity. Some reasoning can be deterministic or consolidated into fewer LangGraph nodes when implementation makes that cleaner.

---

# 14. LangGraph Workflow

LangGraph is used because the project needs:

- explicit state
- inspectable transitions
- conditional branching
- bounded loops
- stop conditions

Conceptual graph:

```text
START
  ↓
load_context
  ↓
diagnose_event
  ↓
get_predictions
  ↓
assess_revenue_risk
  ↓
generate_candidate_actions
  ↓
evaluate_customer_value
  ↓
select_action
  ↓
check_guardrails
  ↓
execute_action
  ↓
monitor_outcome
  ↓
recovery_success?
  ├── YES → record_success → END
  ├── retry_allowed → next_attempt
  ├── escalation_required → escalate → END
  └── otherwise → stop_recovery → END
```

Every loop must be bounded.

The graph must never retry indefinitely.

---

# 15. Agent State

Critical workflow state must be explicit.

Conceptually:

```text
event
customer
merchant

diagnosis

recovery_prediction
churn_prediction

risk_assessment

candidate_actions
selected_action

guardrail_result

action_history
tool_result

outcome
audit_trail

current_step
attempt_count
status
workflow_id
```

Do not rely on free-form chat history as system memory.

Each node should read structured state and return structured updates.

---

# 16. LLM vs ML vs Deterministic Code

| Task | Implementation |
|---|---|
| Load CSV | Pandas |
| Validate schema | Python/Pydantic |
| Feature generation | Python |
| Predict recovery | ML |
| Predict churn | ML |
| Calculate expected recovery | Python |
| Calculate priority | Python |
| Diagnose context | LLM |
| Explain decision | LLM |
| Select among approved candidates | LLM + constraints |
| Check policy | Python |
| Execute action | Python tool |
| Simulate outcome | Python |
| Persist results | Python |
| Generate audit | Python |

## Hard rules

LLM must not:

- invent probabilities
- invent tools
- bypass guardrails
- modify raw source files
- make unrestricted financial decisions

---

# 17. Action Selection

Approved action universe:

```text
retry_now
retry_later
generate_payment_link
send_email
send_whatsapp
request_payment_method_update
offer_retention_incentive
escalate_to_human
stop_recovery
```

Selection pipeline:

```text
Generate valid candidates
        ↓
Remove incompatible actions
        ↓
Consider predictions and context
        ↓
Score/rank candidates
        ↓
LLM reasoning between allowed options
        ↓
Structured selected action
        ↓
Guardrail validation
        ↓
Execute
```

Potential evaluation dimensions:

- expected recovery
- action suitability
- historical effectiveness
- customer friction
- intervention cost
- previous attempts
- merchant policy

---

# 18. Tool Architecture

Tools are deterministic Python functions/services.

Conceptual interface:

```text
ActionRequest
      ↓
Tool
      ↓
ActionResult
```

Every tool returns:

- action_id
- action_type
- status
- timestamp
- message
- metadata

Initial tools:

- `retry_payment()`
- `schedule_retry()`
- `generate_payment_link()`
- `send_email()`
- `send_whatsapp()`
- `offer_retention_incentive()`
- `escalate_to_human()`
- `stop_recovery()`

Simulated tools must still execute real deterministic logic and update workflow state.

---

# 19. Guardrail Engine

Guardrails are deterministic and run after action recommendation but before execution.

## Inputs

- proposed action
- event
- customer
- merchant
- action history

## Outputs

- ALLOW
- BLOCK
- MODIFY
- ESCALATE

## Example rules

- maximum contact attempts
- maximum retry attempts
- cooldown between contacts
- high-value escalation
- low expected value stop
- repeated failure stop
- invalid action/event combinations

Guardrails can override the agent.

Every triggered rule must enter the audit trail.

---

# 20. Outcome Simulation and Monitoring

Real customer interactions are unavailable in the MVP.

Therefore the system requires a separate Outcome Simulator.

## Inputs

- recovery probability
- action type
- event context
- customer context
- previous attempts

## Output

Possible outcomes:

- payment_recovered
- payment_failed
- customer_clicked
- customer_ignored
- customer_retained
- customer_churned
- escalated
- stopped

The simulator should use seeded randomness.

Example:

```text
simulation_seed = fixed value
```

This allows reproducible demos.

The outcome simulator must remain clearly separated from real production action integrations.

---

# 21. Audit Architecture

Every important transition generates an audit entry.

Conceptual fields:

```text
timestamp
workflow_id
event_id
component
step
input_summary
decision
reason
tool
result
metadata
```

Recommended persistence:

```text
audit_logs.jsonl
```

Why JSONL:

- append-friendly
- one record per line
- easy to inspect
- easy to stream/parse

The UI reconstructs an event timeline using audit entries.

---

# 22. Persistence Strategy

No database is required for the initial MVP.

Recommended outputs:

```text
data/outputs/
├── recovery_results.csv
├── decisions.json
├── audit_logs.jsonl
├── analytics_summary.json
└── simulation_runs/
```

## recovery_results.csv

Batch-level event outcomes.

## decisions.json

Structured agent decisions.

## audit_logs.jsonl

Append-only workflow events.

## analytics_summary.json

Precomputed dashboard metrics.

## simulation_runs/

Optional snapshots of demo runs.

Original input files remain immutable.

---

# 23. FastAPI Architecture

FastAPI should remain thin.

## Health

```text
GET /health
```

## Data

```text
POST /data/upload
GET  /data/datasets
POST /data/load-demo
```

## Analysis

```text
POST /analysis/run
GET  /analysis/results
GET  /analysis/event/{event_id}
```

## Recovery

```text
POST /recovery/run/{event_id}
POST /recovery/batch
GET  /recovery/opportunities
```

## Agents

```text
GET /agents/workflow/{workflow_id}
GET /agents/audit/{event_id}
```

## Analytics

```text
GET /analytics/overview
GET /analytics/recovery
GET /analytics/actions
```

Routes should delegate to services rather than containing business logic.

---

# 24. Batch and Single Event Processing

## Single Event Mode

Used for:

- debugging
- detailed agent demonstration
- audit visualization

```text
Event
 ↓
Full workflow
 ↓
Detailed result
```

## Batch Mode

Used for:

- prioritization
- merchant dashboard
- demo dataset processing

```text
Dataset
 ↓
Normalization
 ↓
Batch feature generation
 ↓
ML predictions
 ↓
Risk prioritization
 ↓
Selected event workflows
 ↓
Aggregated results
```

For MVP:

- small datasets may process synchronously
- FastAPI `BackgroundTasks` may be introduced if needed

Do not introduce Redis/Celery unless necessary.

---

# 25. Frontend-Backend Contract

Communication:

```text
REST + JSON
```

## Upload flow

```text
Frontend
  ↓ POST multipart/form-data
Backend
  ↓
Validation
  ↓
Dataset metadata response
```

## Analysis flow

```text
Frontend
  ↓ POST analysis request
Backend
  ↓
Pipeline
  ↓
Structured response
```

## Dashboard flow

```text
Frontend
  ↓ GET analytics
Backend
  ↓
JSON metrics
```

## Event detail flow

```text
Frontend
  ↓ GET event
Backend
  ↓
Event + predictions + decision + audit
```

Frontend types should mirror backend response contracts.

---

# 26. Error Handling and Fallbacks

## File errors

Handle:

- unsupported extension
- corrupted file
- empty dataset
- missing required columns
- invalid values

## ML errors

Handle:

- model missing
- feature mismatch
- inference failure

## LLM errors

Handle:

- timeout
- provider unavailable
- malformed structured output

Fallback:

```text
LLM unavailable
    ↓
Deterministic policy-based action selection
```

## Tool errors

Handle:

- invalid parameters
- simulated execution failure

Result should be logged and workflow should stop/retry/escalate according to policy.

Critical failures must never be silently swallowed.

---

# 27. Configuration

Use environment variables for secrets.

Use centralized config for application behavior.

Configuration categories:

- data paths
- model paths
- scoring weights
- guardrail thresholds
- simulation seed
- LLM provider/model

Required:

```text
.env
.env.example
```

Never commit API keys.

Avoid scattering configuration constants throughout business logic.

---

# 28. Logging and Observability

Structured application logs should capture:

- workflow_id
- event_id
- component
- step
- duration
- selected action
- outcome

Separate:

1. application logs
2. audit logs
3. simulation logs

Logging should help debug the pipeline without flooding the console.

---

# 29. Testing Strategy

## Data tests

- CSV loading
- XLSX loading
- column mapping
- validation
- normalization

## ML tests

- feature schema consistency
- prediction shape
- probabilities within [0,1]

## Risk Engine tests

- expected recovery calculation
- priority categories
- edge cases

## Agent tests

- valid state transitions
- invalid action rejection
- bounded loops
- stop conditions

## Guardrail tests

- retry limits
- contact limits
- escalation

## Tool tests

- typed inputs
- typed outputs
- state updates

## Integration tests

```text
File
 ↓
Normalize
 ↓
Features
 ↓
Predictions
 ↓
Risk
 ↓
Agent
 ↓
Guardrail
 ↓
Tool
 ↓
Outcome
```

Use mocks for external LLM calls where possible.

---

# 30. Performance Principles

The MVP should optimize for clarity before scale.

Recommended approach:

- batch Pandas operations
- batch ML inference
- avoid per-row expensive LLM calls for every event
- prioritize top events for detailed agent workflows
- cache loaded models in memory
- avoid repeated file reads

Important design consideration:

For a batch of 10,000 events:

1. run deterministic processing and ML predictions in batch
2. calculate priority scores
3. rank events
4. run deeper agent workflows selectively on meaningful opportunities

This is faster, cheaper, and architecturally more credible than calling an LLM 10,000 times.

---

# 31. Development Rules

Any developer working on this repository must follow:

1. Read `PROJECT.md` and this document before architectural changes.
2. Do not introduce infrastructure without a concrete need.
3. Keep FastAPI route handlers thin.
4. Keep business logic out of the frontend.
5. Keep ML, agent, tool, and guardrail responsibilities separate.
6. Do not use LLMs for deterministic calculations.
7. Do not let agents bypass guardrails.
8. Do not mutate raw uploaded files.
9. Do not generate the whole project in one implementation step.
10. Test each layer before integration.
11. Prefer simple modules over premature abstraction.
12. Update documentation when architecture materially changes.

---

# 32. Implementation Sequence

Implementation should proceed in this order.

## Phase 1 — Foundation

- repository setup
- Python environment
- FastAPI health endpoint
- React shell
- configuration

## Phase 2 — Data Layer

- synthetic dataset generator
- CSV/XLSX loader
- validation
- normalization
- internal schemas

## Phase 3 — Feature Layer

- feature engineering
- preprocessing pipeline
- processed outputs

## Phase 4 — ML Layer

- recovery baseline
- churn baseline
- evaluation
- model serialization
- inference services

## Phase 5 — Revenue Risk Engine

- expected recovery
- prioritization
- categories

## Phase 6 — Agent Workflow

- AgentState
- LangGraph
- diagnosis
- candidate actions
- action selection

## Phase 7 — Guardrails and Tools

- policies
- action validation
- simulated tools

## Phase 8 — Outcome Monitoring

- outcome simulator
- recovery results
- audit logs

## Phase 9 — API Integration

- upload
- analysis
- event details
- analytics

## Phase 10 — Frontend

- dashboard
- opportunities
- event detail
- audit timeline

## Phase 11 — End-to-End Demo

- seeded demo dataset
- reproducible simulation
- metrics validation
- UI polish

---

# 33. Technical Decisions and Deferred Items

## Locked for MVP

- file-first architecture
- CSV/XLSX input
- Pandas processing
- FastAPI thin backend
- React frontend
- Scikit-learn/XGBoost experimentation
- LangGraph for explicit workflows
- simulated action tools
- deterministic guardrails
- JSON/JSONL output persistence
- no PostgreSQL requirement

## Intentionally deferred

The following should only be added if a real need emerges:

- PostgreSQL
- Redis
- Celery
- Docker Compose
- authentication
- real payment gateway integration
- real WhatsApp integration
- background worker infrastructure
- vector database
- reinforcement learning
- multi-tenant production architecture

---

# Final Technical Principle

The project should feel sophisticated because its intelligence loop is real:

```text
DATA
 ↓
NORMALIZATION
 ↓
FEATURES
 ↓
PREDICTION
 ↓
PRIORITIZATION
 ↓
REASONING
 ↓
BOUNDED DECISION
 ↓
GUARDRAIL VALIDATION
 ↓
ACTION
 ↓
OUTCOME
 ↓
MEASUREMENT
```

It should **not** feel sophisticated merely because it contains many frameworks.

The preferred engineering decision is always:

> **Use the simplest architecture that can credibly demonstrate the full Revenue Recovery Orchestrator.**
