# Revenue Recovery Orchestrator — Development Plan

> **Companion documents:** `PROJECT.md`, `TECHNICAL_SPEC.md`, `DATA_SPEC.md`, `AGENT_SPEC.md`, `UI_UX_SPEC.md`  
> **Purpose:** Define the build sequence for RevenueOS — from data pipeline through ML, agent workflow, API, and UI.

---

# 1. Development Philosophy

This project must **not** be built screen-first.

The correct build order is:

```text
DATA
 ↓
FEATURES
 ↓
ML
 ↓
RISK ENGINE
 ↓
AGENT WORKFLOW
 ↓
TOOLS + OUTCOMES
 ↓
API
 ↓
UI
 ↓
DEMO POLISH
```

Why?

Because the UI should visualize a real working system, not force the backend to catch up later.

## Core rule

> **Build one complete vertical slice before adding sophistication.**

The first working version should be able to:

```text
Load CSV
↓
Detect revenue event
↓
Build features
↓
Predict recovery/churn
↓
Calculate priority
↓
Select action
↓
Execute simulated action
↓
Return outcome
```

Once this works end-to-end, improve it.

---

# 2. MVP Definition

The MVP is complete when a user can:

1. Upload/load merchant data
2. Analyze revenue events
3. See revenue at risk
4. See recoverable opportunity
5. See prioritized events
6. Open one event
7. Inspect customer/payment context
8. See recovery + churn predictions
9. Run the agent workflow
10. See candidate actions
11. See selected action
12. See guardrail validation
13. See simulated execution
14. See outcome and audit trail

Everything else is secondary.

---

# 3. Recommended Build Phases

```text
PHASE 0  → Project Foundation
PHASE 1  → Synthetic Data Engine
PHASE 2  → Data Processing Pipeline
PHASE 3  → Feature Engineering
PHASE 4  → ML Models
PHASE 5  → Revenue Risk Engine
PHASE 6  → Agentic Workflow
PHASE 7  → Simulated Tools + Outcomes
PHASE 8  → FastAPI Integration
PHASE 9  → Frontend MVP
PHASE 10 → End-to-End Integration
PHASE 11 → Testing + Hardening
PHASE 12 → Demo + Buildathon Polish
```

Do not jump phases randomly.

---

# PHASE 0 — PROJECT FOUNDATION

## Goal

Create a clean repository and establish project contracts.

## Tasks

### Repository structure

Create:

```text
revenue-recovery-orchestrator/
│
├── backend/
│   ├── app/
│   ├── data/
│   ├── models/
│   ├── services/
│   ├── agents/
│   ├── tools/
│   ├── schemas/
│   └── tests/
│
├── frontend/
│
├── docs/
│
├── scripts/
│
├── artifacts/
│
├── .env.example
├── README.md
└── requirements.txt
```

Exact structure may evolve, but avoid mixing everything into one directory.

### Move specifications

Place all project docs in:

```text
/docs
```

Required:

```text
PROJECT.md
TECHNICAL_SPEC.md
DATA_SPEC.md
AGENT_SPEC.md
UI_UX_SPEC.md
DEVELOPMENT_PLAN.md
```

### Environment

Create:

```text
.env.example
```

Example variables:

```text
LLM_API_KEY=
LLM_MODEL=
APP_ENV=development
RANDOM_SEED=42
```

Do not commit secrets.

### Basic quality setup

Add:

- `.gitignore`
- environment instructions
- basic logging configuration

## Deliverable

A clean repository that can be opened and understood without reading implementation code.

## Phase Exit Criteria

- [ ] Repository structure exists
- [ ] Docs are organized
- [ ] Environment setup works
- [ ] Backend can start
- [ ] Frontend can start

---

# PHASE 1 — SYNTHETIC DATA ENGINE

## Goal

Create a believable merchant ecosystem.

This phase is foundational.

Do not build ML models on random data.

---

## 1.1 Build Data Generator

Create:

```text
scripts/generate_synthetic_data.py
```

The generator should produce:

```text
customers.csv
transactions.csv
subscriptions.csv
revenue_events.csv
intervention_history.csv
metadata.json
```

---

## 1.2 Generation Order

Strict generation sequence:

```text
MERCHANT
 ↓
CUSTOMERS
 ↓
LATENT CUSTOMER BEHAVIOR
 ↓
SUBSCRIPTIONS
 ↓
TRANSACTIONS
 ↓
PAYMENT FAILURES
 ↓
REVENUE EVENTS
 ↓
INTERVENTIONS
 ↓
OUTCOMES
```

---

## 1.3 Customer Generation

Generate approximately:

```text
2,000–5,000 customers
```

Each customer receives realistic behavioral characteristics.

Internal latent variables may include:

```text
payment_reliability
engagement
value_tendency
churn_tendency
```

These variables should influence observed data.

---

## 1.4 Transaction Generation

Generate:

```text
20,000–50,000 transactions
```

Include:

```text
successful payments
failed payments
different payment methods
recurring payments
different amounts
different failure reasons
```

Transactions must correlate with customer characteristics.

---

## 1.5 Revenue Event Generation

Create meaningful events.

Examples:

```text
payment_failed
subscription_payment_failed
repeated_payment_failure
high_value_payment_failure
```

Each event should have enough context to support downstream analysis.

---

## 1.6 Intervention History

Generate historical actions and outcomes.

Example:

```text
Event
 ↓
retry_later
 ↓
recovered
```

or:

```text
Event
 ↓
retry_now
 ↓
failed
 ↓
payment_link
 ↓
recovered
```

This history will later support:

- context
- action effectiveness
- future feedback loops

---

## 1.7 Synthetic Data Validation

Create validation checks.

Check:

```text
duplicate IDs
invalid dates
negative amounts
missing required columns
broken relationships
class distributions
```

Also inspect:

```text
recovery rate
churn rate
failure reason distribution
customer segments
event amounts
```

## Deliverable

A reproducible synthetic dataset.

## Phase Exit Criteria

- [ ] Same seed generates consistent dataset structure
- [ ] All required CSVs exist
- [ ] Relationships are valid
- [ ] Recovery labels are not random
- [ ] Churn labels are not random
- [ ] Dataset has realistic distributions

---

# PHASE 2 — DATA PROCESSING PIPELINE

## Goal

Convert raw files into canonical clean datasets.

---

## 2.1 File Loader

Support:

```text
CSV
XLSX
```

Primary library:

```text
pandas
```

---

## 2.2 Schema Detection

Implement:

```text
column normalization
column alias mapping
required field validation
```

Example:

```text
user_id → customer_id
amount → amount_at_risk
txn_id → transaction_id
```

---

## 2.3 Data Cleaner

Handle:

```text
duplicate records
missing values
invalid timestamps
invalid categories
string normalization
numeric conversion
```

---

## 2.4 Canonical Objects

Create Pydantic schemas.

Example conceptual schemas:

```text
Customer
Transaction
Subscription
RevenueEvent
Intervention
```

The backend should operate on known structures rather than arbitrary DataFrames everywhere.

---

## 2.5 Context Joiner

Build functions that can assemble:

```text
Event
+
Customer
+
Transaction history
+
Subscription
+
Intervention history
```

Output:

```text
EventContext
```

This becomes one of the most important internal objects.

---

## Deliverable

A pipeline:

```text
Raw CSV
↓
Validated
↓
Normalized
↓
Canonical Data
↓
Event Context
```

## Phase Exit Criteria

- [ ] CSV works
- [ ] XLSX works
- [ ] validation report exists
- [ ] canonical schemas exist
- [ ] context can be assembled for event
- [ ] missing optional data does not crash pipeline

---

# PHASE 3 — FEATURE ENGINEERING

## Goal

Transform raw context into model-ready features.

Build this before training models.

---

# 3.1 Recovery Features

Possible features:

```text
amount_at_risk
attempt_number
payment_success_rate
previous_failures
previous_recoveries
customer_tenure
engagement_score
days_since_last_activity
is_recurring
failure_reason
payment_method
```

Derived features:

```text
recent_failure_rate
historical_recovery_rate
customer_value_ratio
failure_frequency
```

---

# 3.2 Churn Features

Possible features:

```text
tenure_days
total_spend
customer_ltv
engagement_score
activity_trend
payment_success_rate
previous_failures
failed_cycles
recent_payment_failures
days_since_last_activity
```

---

# 3.3 Feature Pipeline

Create:

```text
backend/app/services/features/
```

Suggested files:

```text
recovery_features.py
churn_features.py
feature_utils.py
```

Avoid duplicated feature logic between training and inference.

---

# 3.4 Feature Contracts

Training and inference must use identical feature definitions.

This is critical.

Bad:

```text
training features ≠ production features
```

Correct:

```text
shared feature builder
      ↓
training
      +
inference
```

---

## Deliverable

Feature matrices for both models.

## Phase Exit Criteria

- [ ] recovery feature builder works
- [ ] churn feature builder works
- [ ] no target leakage
- [ ] training and inference share feature logic
- [ ] missing data handled

---

# PHASE 4 — MACHINE LEARNING MODELS

## Goal

Build credible baseline models.

Do not chase advanced deep learning.

Tabular data + hackathon constraints = simple models first.

---

# 4.1 Recovery Model

Question:

```text
What is the probability that this revenue event can be recovered?
```

Start with:

```text
Logistic Regression
Random Forest
XGBoost / LightGBM (if justified)
```

Recommended approach:

```text
Baseline model
↓
Evaluate
↓
Improve only if needed
```

---

# 4.2 Churn Model

Question:

```text
What is the probability that this customer is at risk of churn?
```

Same strategy:

```text
Logistic Regression baseline
↓
Tree-based model comparison
```

---

# 4.3 Evaluation

Track:

```text
ROC-AUC
Precision
Recall
F1
Confusion Matrix
```

Do not optimize for accuracy alone.

---

# 4.4 Model Artifacts

Store:

```text
artifacts/
├── recovery_model.pkl
├── churn_model.pkl
├── recovery_feature_schema.json
├── churn_feature_schema.json
└── metrics.json
```

---

# 4.5 Model Inference Service

Create:

```text
PredictionService
```

Methods:

```python
predict_recovery(context)
predict_churn(context)
```

Output structured predictions.

---

## Deliverable

Two working models exposed through one service layer.

## Phase Exit Criteria

- [ ] recovery model trained
- [ ] churn model trained
- [ ] metrics recorded
- [ ] artifacts persisted
- [ ] inference works on new event
- [ ] feature schema validated

---

# PHASE 5 — REVENUE RISK ENGINE

## Goal

Convert predictions into business prioritization.

This is where ML becomes product intelligence.

---

# 5.1 Inputs

```text
amount_at_risk
recovery_probability
churn_probability
customer_ltv
urgency
```

---

# 5.2 Outputs

```text
expected_recovery_value
priority_score
priority_category
```

---

# 5.3 Initial Formula

Start simple and explainable.

Example:

```text
Expected Recovery Value
=
Amount at Risk × Recovery Probability
```

Then incorporate contextual factors into priority.

Conceptually:

```text
Priority Score
=
Expected Recovery Value
+
Customer Value Signal
+
Churn Risk Signal
+
Urgency Signal
```

Normalize components before combining.

Do not create an unnecessarily complex formula.

---

# 5.4 Priority Categories

Map scores to:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Thresholds should be configurable.

---

# 5.5 Explainability

Risk engine should return contributing factors.

Example:

```json
{
  "priority": "HIGH",
  "priority_score": 82,
  "factors": [
    "High immediate revenue at risk",
    "Strong recovery probability",
    "Elevated customer value"
  ]
}
```

---

## Deliverable

Every event can be ranked.

## Phase Exit Criteria

- [ ] expected value calculated
- [ ] priority score calculated
- [ ] categories assigned
- [ ] ranking works
- [ ] explanations generated
- [ ] thresholds configurable

---

# PHASE 6 — AGENTIC WORKFLOW

## Goal

Build the controlled decision loop.

Do not begin with complicated multi-agent conversations.

---

# 6.1 Install and Configure LangGraph

Create:

```text
backend/app/agents/
```

Suggested structure:

```text
agents/
├── graph.py
├── state.py
├── nodes/
│   ├── context.py
│   ├── diagnosis.py
│   ├── predictions.py
│   ├── risk.py
│   ├── candidates.py
│   ├── decision.py
│   ├── guardrails.py
│   ├── execution.py
│   └── monitoring.py
│
└── prompts/
    ├── diagnosis.py
    └── decision.py
```

---

# 6.2 Build State First

Define typed workflow state before nodes.

State should include:

```text
event
context
predictions
risk_assessment
candidate_actions
selected_action
guardrail_result
action_history
latest_tool_result
outcome
status
audit_entries
```

---

# 6.3 Implement Deterministic Nodes First

Before calling any LLM:

```text
assemble_context
get_predictions
assess_risk
generate_candidates
validate_action
```

Test each independently.

---

# 6.4 Add Diagnostic LLM Node

LLM task:

```text
Explain what happened based on supplied context.
```

Must:

- return structured output
- not invent numbers
- not select arbitrary tools

---

# 6.5 Add Decision LLM Node

Inputs:

```text
diagnosis
predictions
risk
candidate actions
history
```

Output:

```text
selected action
reason
alternative considered
```

Constraint:

```text
Selected action ∈ Candidate actions
```

---

# 6.6 Conditional Routing

Routes:

```text
SUCCESS
RETRY
ALTERNATIVE_ACTION
ESCALATE
STOP
```

Implement explicit routing functions.

---

## Deliverable

A working agent graph for one event.

## Phase Exit Criteria

- [ ] state works
- [ ] deterministic nodes work
- [ ] LLM structured output works
- [ ] candidate constraints work
- [ ] routing works
- [ ] loops bounded
- [ ] terminal states exist

---

# PHASE 7 — SIMULATED TOOLS + OUTCOMES

## Goal

Make the agent workflow operational.

The agent must do more than recommend.

---

# 7.1 Tool Registry

Create:

```text
tools/
├── registry.py
├── payment_tools.py
├── communication_tools.py
├── escalation_tools.py
└── simulation.py
```

---

# 7.2 MVP Tools

Implement:

```text
retry_now
retry_later
generate_payment_link
send_email
send_whatsapp
payment_method_update
retention_offer
escalate_to_human
stop_recovery
```

All can be simulated.

---

# 7.3 Common Tool Result

Every tool returns:

```json
{
  "action_id": "...",
  "action_type": "...",
  "status": "...",
  "timestamp": "...",
  "metadata": {}
}
```

---

# 7.4 Outcome Simulation

Outcome probabilities should depend on context.

Example:

```text
network_error
+
retry_now
→ relatively high success probability
```

```text
card_expired
+
retry_now
→ low success probability
```

```text
card_expired
+
payment_method_update
→ higher success probability
```

This makes action choice meaningful.

Do not randomly return outcomes independent of actions.

---

# 7.5 Guardrails

Implement:

```text
max retries
max contacts
cooldown
allowed actions
escalation threshold
stop threshold
```

Guardrails should be deterministic.

---

## Deliverable

Full:

```text
Decision
↓
Guardrail
↓
Tool
↓
Outcome
↓
Next Route
```

## Phase Exit Criteria

- [ ] tools execute
- [ ] tool outputs standardized
- [ ] outcomes context-dependent
- [ ] guardrails block invalid actions
- [ ] retry limits work
- [ ] escalation works
- [ ] workflow terminates

---

# PHASE 8 — FASTAPI INTEGRATION

## Goal

Expose the working intelligence engine through clean APIs.

Build APIs after core logic works.

---

# 8.1 API Structure

Suggested:

```text
api/
├── health.py
├── upload.py
├── analytics.py
├── events.py
└── workflows.py
```

---

# 8.2 Minimum Endpoints

## Health

```text
GET /health
```

## Analyze Dataset

```text
POST /analyze
```

## Dashboard Summary

```text
GET /dashboard/summary
```

## Opportunities

```text
GET /events
```

## Event Detail

```text
GET /events/{event_id}
```

## Run Agent

```text
POST /events/{event_id}/run-agent
```

## Workflow Detail

```text
GET /workflows/{workflow_id}
```

---

# 8.3 Response Schemas

All API responses should use Pydantic models.

Avoid returning raw DataFrames or arbitrary dictionaries.

---

# 8.4 API Testing

Test:

- success
- invalid input
- missing event
- malformed file
- workflow errors

---

## Deliverable

Frontend can consume the complete backend.

## Phase Exit Criteria

- [ ] all major endpoints work
- [ ] schemas documented
- [ ] errors readable
- [ ] no raw internal exceptions exposed

---

# PHASE 9 — FRONTEND MVP

## Goal

Build the product around real backend responses.

Recommended order:

```text
App Shell
↓
Upload
↓
Dashboard
↓
Opportunities
↓
Event Detail
↓
Agent Activity
```

---

# 9.1 App Shell

Build:

```text
Sidebar
Top navigation
Page container
```

Do this once.

---

# 9.2 Upload Screen

Features:

- drag/drop
- file selection
- demo dataset button
- validation status
- analysis progress

---

# 9.3 Dashboard

Build in this order:

1. KPI cards
2. revenue funnel
3. priority distribution
4. top opportunities

Use real API data.

---

# 9.4 Opportunities

Add:

- table
- sorting
- filters
- search

Do not overbuild filtering.

---

# 9.5 Event Detail

This is the highest-priority UI page.

Implement:

```text
Event context
Customer context
Predictions
Risk assessment
AI recommendation
Candidate actions
Agent timeline
Outcome
```

---

# 9.6 Agent Activity

Show:

- active workflows
- completed workflows
- recent actions
- escalations
- outcomes

---

## Deliverable

A complete user-facing product.

## Phase Exit Criteria

- [ ] upload works
- [ ] dashboard works
- [ ] events can be inspected
- [ ] agent workflow visible
- [ ] no mock data remains in main flow

---

# PHASE 10 — END-TO-END INTEGRATION

## Goal

Validate the complete story.

Run:

```text
Load dataset
↓
Analyze all events
↓
Rank opportunities
↓
Open event
↓
Run agent
↓
Execute action
↓
Observe outcome
↓
Refresh UI
```

---

# 10.1 Critical Integration Test

Choose three representative events:

### Scenario A

Temporary failure:

```text
network error
→ retry
→ recovered
```

### Scenario B

Payment method problem:

```text
expired card
→ payment method update
→ recovered
```

### Scenario C

Complex high-value case:

```text
repeated failure
+
high churn
+
high LTV
→ escalation
```

All three should work reliably.

These become demo scenarios.

---

## Deliverable

Three end-to-end stories.

## Phase Exit Criteria

- [ ] all scenarios work
- [ ] UI reflects backend state
- [ ] audit trail complete
- [ ] outcomes consistent

---

# PHASE 11 — TESTING + HARDENING

## Goal

Remove fragile behavior.

---

# 11.1 Backend Tests

Test:

```text
data validation
feature engineering
prediction service
risk scoring
candidate generation
guardrails
tools
routing
```

---

# 11.2 Agent Tests

Important tests:

```text
LLM selects invalid action
→ blocked/fallback
```

```text
LLM malformed JSON
→ retry/fallback
```

```text
tool fails
→ alternative/escalation
```

```text
retry limit reached
→ no further retry
```

---

# 11.3 UI Tests

Check:

- loading
- empty states
- API errors
- long event tables
- workflow pending states

---

# 11.4 Demo Reliability

The demo must not depend on unpredictable LLM behavior alone.

For critical demo scenarios:

- structured outputs
- deterministic guardrails
- deterministic fallback
- optionally seeded outcome simulation

Reliability > randomness.

---

## Deliverable

Stable demo build.

---

# PHASE 12 — BUILDATHON POLISH

## Goal

Optimize for judges.

This phase should focus on storytelling, not adding random features.

---

# 12.1 Product Story

The pitch should communicate:

```text
Failed payments create fragmented recovery workflows.

Existing systems can retry payments or send reminders.

Our system goes further:

It understands event context,
predicts recovery and churn,
prioritizes revenue opportunity,
selects context-aware actions,
executes within guardrails,
and learns from outcomes.
```

---

# 12.2 Demo Flow

Recommended demo:

## 1. Problem

```text
Merchant has thousands of payment events.
Manual recovery cannot prioritize everything.
```

## 2. Dashboard

Show:

```text
₹12.4L at risk
₹8.1L recoverable
42 high-priority opportunities
```

Use actual generated values, not fixed numbers.

## 3. Opportunity

Open one high-value event.

## 4. Context

Show:

- customer behavior
- payment history
- churn context

## 5. Intelligence

Show:

- recovery probability
- churn probability
- expected value

## 6. Agent

Run workflow.

Show:

```text
diagnosis
↓
candidate actions
↓
decision
↓
guardrail
↓
execution
```

## 7. Outcome

Show recovery/escalation.

## 8. Differentiator

Explain:

```text
We are not building another payment retry system.

We are building a bounded AI decision layer above revenue events.
```

---

# 13. Suggested Development Order

Do not build the whole application at once.

Use incremental steps.

Recommended sequence:

```text
1. Inspect project docs
2. Create repository skeleton
3. Build synthetic generator
4. Test generated CSVs
5. Build data ingestion
6. Build feature pipeline
7. Train recovery model
8. Train churn model
9. Build risk engine
10. Test event ranking
11. Build agent state
12. Build deterministic nodes
13. Add LLM nodes
14. Add tools
15. Test full workflow
16. Build APIs
17. Build frontend
18. Integrate
19. Polish
```

After every major step:

```text
Run
↓
Test
↓
Inspect
↓
Fix
↓
Commit
```

Never allow large untested changes to accumulate.

---

# 14. Git Strategy

Suggested branches:

```text
main
develop
feature/data
feature/ml
feature/agent
feature/api
feature/frontend
```

For solo development, this can be simplified.

Minimum recommendation:

```text
main
develop
```

Commit after meaningful milestones.

Example commits:

```text
feat: add synthetic merchant data generator

feat: implement canonical data ingestion pipeline

feat: add recovery and churn prediction services

feat: implement revenue prioritization engine

feat: add langgraph recovery workflow

feat: add simulated recovery tools

feat: integrate event analysis API

feat: build revenue intelligence dashboard
```

---

# 15. Suggested Milestones

## Milestone 1 — Data Ready

```text
Synthetic data generated and validated.
```

## Milestone 2 — Intelligence Ready

```text
Features + models + risk scoring work.
```

## Milestone 3 — Agent Ready

```text
One event can complete workflow.
```

## Milestone 4 — Product Ready

```text
API + frontend integrated.
```

## Milestone 5 — Demo Ready

```text
Three reliable scenarios.
```

---

# 16. Dependency Map

```text
Synthetic Data
      ↓
Data Pipeline
      ↓
Feature Engineering
      ↓
ML Models
      ↓
Risk Engine
      ↓
Agent Workflow
      ↓
Tools + Outcomes
      ↓
FastAPI
      ↓
Frontend
      ↓
Demo
```

Do not invert this dependency chain.

---

# 17. What to Fake vs What Must Be Real

This is important for hackathon scope.

## Must Be Real

- data processing
- feature engineering
- ML inference
- risk calculations
- event prioritization
- agent workflow
- candidate selection
- guardrails
- state transitions
- audit trail

## Can Be Simulated

- payment retries
- payment links
- emails
- WhatsApp
- human escalation queue
- final external payment processing

The core intelligence must be real.

External integrations can be simulated.

---

# 18. Time Allocation Philosophy

Do not spend equal time everywhere.

Recommended priority:

```text
Core Intelligence       ████████████████████
Agent Workflow          ████████████████
Data + ML               ██████████████
UI                       ████████████
Demo Polish              ████████
Infrastructure           ████
```

The project wins on:

- product insight
- technical architecture
- believable intelligence
- polished demo

Not on Kubernetes or authentication.

---

# 19. Scope Control Rules

When considering a new feature, ask:

### Does it improve the core loop?

```text
Event
→ Intelligence
→ Action
→ Outcome
```

If no, postpone it.

### Does it help judges understand the value?

If yes, consider it.

### Does it create significant engineering complexity?

If yes, simplify.

---

# 20. Features Explicitly Deferred

Do not build unless time remains:

- real Razorpay production integration
- authentication
- user management
- multi-tenant database
- real WhatsApp API
- real email delivery
- real-time WebSockets
- reinforcement learning
- autonomous model retraining
- complex multi-agent debates
- mobile application
- billing

These are distractions for MVP.

---

# 21. Final Testing Checklist

Before submission:

## Data

- [ ] dataset loads
- [ ] invalid data handled
- [ ] demo scenario works

## ML

- [ ] models load
- [ ] predictions valid
- [ ] metrics recorded

## Risk Engine

- [ ] expected value correct
- [ ] priority ranking correct

## Agent

- [ ] valid candidates only
- [ ] guardrails work
- [ ] fallback works
- [ ] loops terminate

## Tools

- [ ] execution logged
- [ ] outcomes returned

## API

- [ ] all critical endpoints work

## UI

- [ ] dashboard understandable
- [ ] event detail complete
- [ ] timeline visible

## Demo

- [ ] three scenarios tested
- [ ] no dependency on unstable randomness
- [ ] demo flow rehearsed

---

# 22. Definition of Done

The project is done when it can demonstrate this complete loop:

```text
MERCHANT DATA
      ↓
DATA NORMALIZATION
      ↓
REVENUE EVENT DETECTION
      ↓
CUSTOMER CONTEXT
      ↓
ML PREDICTIONS
      ↓
REVENUE PRIORITIZATION
      ↓
AI DIAGNOSIS
      ↓
VALID ACTION CANDIDATES
      ↓
AI DECISION
      ↓
GUARDRAIL VALIDATION
      ↓
SIMULATED EXECUTION
      ↓
OUTCOME
      ↓
AUDIT TRAIL
```

And a new user can understand the product's value within a few minutes.

---

# Final Development Principle

The biggest risk is not that the project will be too simple.

The biggest risk is building too many disconnected features.

Every implementation decision should strengthen this single story:

> **Revenue events should not be treated as isolated failures. An intelligent system should understand the customer context, estimate recoverable value, account for churn risk, choose an appropriate next action within policy boundaries, and use outcomes to improve future recovery decisions.**

Build depth around that loop.

Do not build breadth around everything else.

---

# FINAL BUILD ORDER — QUICK REFERENCE

```text
PHASE 0
Project Foundation

PHASE 1
Synthetic Data Engine

PHASE 2
Data Processing Pipeline

PHASE 3
Feature Engineering

PHASE 4
ML Models

PHASE 5
Revenue Risk Engine

PHASE 6
Agentic Workflow

PHASE 7
Tools + Outcome Simulation

PHASE 8
FastAPI Integration

PHASE 9
Frontend MVP

PHASE 10
End-to-End Integration

PHASE 11
Testing + Hardening

PHASE 12
Buildathon Demo Polish
```

> **First make it work. Then make it reliable. Then make it impressive.**
