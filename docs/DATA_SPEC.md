# Revenue Recovery Orchestrator — Data Specification

> **Companion documents:** `PROJECT.md`, `TECHNICAL_SPEC.md`  
> **Purpose:** Define the complete data model, file schemas, relationships, synthetic data strategy, labels, and data pipeline contracts for the Revenue Recovery Orchestrator.

---

# Table of Contents

1. Purpose
2. Data Philosophy
3. MVP Dataset Strategy
4. Canonical Data Model
5. Entity Relationships
6. Core Input Files
7. customers.csv
8. transactions.csv
9. subscriptions.csv
10. revenue_events.csv
11. intervention_history.csv
12. Merchant Configuration
13. Canonical Revenue Event
14. Column Naming and Alias Mapping
15. Data Types and Validation
16. Data Relationships
17. Synthetic Data Generation Strategy
18. Synthetic Customer Generation
19. Synthetic Transaction Generation
20. Synthetic Subscription Generation
21. Synthetic Revenue Event Generation
22. Synthetic Intervention History
23. Realistic Correlations
24. Recovery Model Dataset
25. Churn Model Dataset
26. Target Label Generation
27. Feature Availability Rules
28. Missing Data Strategy
29. Class Imbalance Strategy
30. Train/Validation/Test Strategy
31. Demo Dataset Profiles
32. Data Pipeline
33. Processed Outputs
34. Data Quality Checks
35. Privacy and PII Rules
36. Data Versioning
37. Sample Records
38. Acceptance Criteria

---

# 1. Purpose

The Revenue Recovery Orchestrator is driven by structured data.

The data layer must support two goals simultaneously:

1. **A realistic hackathon demonstration**
2. **Meaningful ML and agentic decisions**

This document defines exactly what data exists, what each file contains, how files relate to each other, and how synthetic demo data should be generated.

The MVP is intentionally **file-first**.

Primary input:

```text
CSV / XLSX
```

Primary processing:

```text
Pandas
```

Primary internal representation:

```text
Canonical Python / Pydantic objects + DataFrames
```

Primary outputs:

```text
CSV + JSON + JSONL
```

---

# 2. Data Philosophy

The dataset must not be random noise.

Synthetic data should create believable relationships such as:

- repeated payment failures → higher churn risk
- strong historical payment behavior → higher recovery probability
- temporary payment failure → potentially recoverable
- repeated failed attempts → lower marginal recovery probability
- high-value customers → greater future revenue at risk
- recent engagement → lower churn probability
- successful recovery history → useful recovery signal
- certain actions → better outcomes for certain event contexts

The project should demonstrate a meaningful chain:

```text
RAW DATA
   ↓
BEHAVIORAL SIGNALS
   ↓
FEATURES
   ↓
ML PREDICTIONS
   ↓
REVENUE PRIORITIZATION
   ↓
AGENT DECISION
   ↓
ACTION
   ↓
OUTCOME
```

Synthetic labels must therefore be generated from structured underlying logic, not independently random values.

---

# 3. MVP Dataset Strategy

The MVP uses five primary datasets.

```text
data/synthetic/
│
├── customers.csv
├── transactions.csv
├── subscriptions.csv
├── revenue_events.csv
└── intervention_history.csv
```

Optional:

```text
merchant_config.json
```

## Why multiple files?

A single giant CSV is easier initially but less realistic.

Multiple related datasets allow the system to demonstrate:

- data joining
- context construction
- customer history
- payment behavior
- subscription context
- previous intervention outcomes

However, the system must also support a simplified upload mode.

### Minimum required file

For basic analysis:

```text
revenue_events.csv
```

### Rich analysis mode

For better ML and agent context:

```text
customers.csv
+ transactions.csv
+ subscriptions.csv
+ revenue_events.csv
+ intervention_history.csv
```

---

# 4. Canonical Data Model

The conceptual data model is:

```text
MERCHANT
   │
   ├─────────────── CUSTOMER
   │                    │
   │                    ├──── TRANSACTIONS
   │                    │
   │                    ├──── SUBSCRIPTIONS
   │                    │
   │                    ├──── REVENUE EVENTS
   │                    │
   │                    └──── INTERVENTION HISTORY
   │
   └─────────────── POLICIES
```

Primary entities:

1. Merchant
2. Customer
3. Transaction
4. Subscription
5. Revenue Event
6. Intervention
7. Recovery Outcome

---

# 5. Entity Relationships

## Merchant → Customer

One merchant can have many customers.

```text
merchant_id
    1
    │
    └────── N customers
```

## Customer → Transactions

One customer can have many transactions.

```text
customer_id
    1
    │
    └────── N transactions
```

## Customer → Subscriptions

A customer can have zero or more subscriptions.

## Customer → Revenue Events

A customer can have multiple failed payment or churn-risk events.

## Revenue Event → Intervention History

One event can trigger multiple recovery attempts.

```text
event
  │
  ├── retry attempt
  ├── payment link
  ├── email
  └── escalation
```

---

# 6. Core Input Files

| File | Required | Purpose |
|---|---|---|
| customers.csv | Recommended | Customer context |
| transactions.csv | Recommended | Historical payment behavior |
| subscriptions.csv | Optional | Recurring revenue context |
| revenue_events.csv | Required | Events to analyze |
| intervention_history.csv | Optional | Previous recovery attempts |
| merchant_config.json | Optional | Policy configuration |

---

# 7. customers.csv

## Purpose

Provides customer-level context used by:

- churn prediction
- recovery prediction
- customer value estimation
- agent reasoning

## Schema

| Column | Type | Required | Description |
|---|---|---|---|
| customer_id | string | Yes | Unique customer identifier |
| merchant_id | string | Yes | Merchant identifier |
| customer_segment | string | No | Value/behavior segment |
| signup_date | datetime | Yes | Customer acquisition date |
| tenure_days | integer | Derived | Days since signup |
| total_orders | integer | No | Historical orders |
| total_spend | float | No | Historical spend |
| avg_order_value | float | No | Average transaction value |
| payment_success_rate | float | No | Historical success ratio |
| previous_failures | integer | No | Historical failed payments |
| previous_recoveries | integer | No | Successful recoveries |
| engagement_score | float | No | Normalized engagement score 0-1 |
| activity_trend | string | No | increasing/stable/declining |
| customer_ltv | float | No | Estimated lifetime value |
| last_activity_date | datetime | No | Most recent activity |
| churned | integer | Training only | Historical churn label |

## customer_segment values

Recommended:

```text
VIP
HIGH_VALUE
REGULAR
NEW
AT_RISK
```

## activity_trend values

```text
increasing
stable
declining
inactive
```

---

# 8. transactions.csv

## Purpose

Stores payment history.

Used to calculate:

- payment success behavior
- failure frequency
- recent payment patterns
- historical transaction value

## Schema

| Column | Type | Required | Description |
|---|---|---|---|
| transaction_id | string | Yes | Unique transaction |
| customer_id | string | Yes | Customer reference |
| merchant_id | string | Yes | Merchant reference |
| transaction_timestamp | datetime | Yes | Transaction time |
| amount | float | Yes | Transaction amount |
| currency | string | Yes | Currency |
| payment_method | string | Yes | Payment method |
| transaction_status | string | Yes | success/failed/pending |
| failure_reason | string | No | Failure category |
| attempt_number | integer | No | Attempt sequence |
| subscription_id | string | No | Related subscription |
| is_recurring | boolean | No | Recurring payment flag |

## payment_method values

Suggested:

```text
card
upi
netbanking
wallet
bank_transfer
```

## transaction_status

```text
success
failed
pending
```

## failure_reason values

Suggested normalized categories:

```text
insufficient_funds
card_expired
bank_declined
network_error
authentication_failed
payment_timeout
upi_failure
unknown
```

---

# 9. subscriptions.csv

## Purpose

Provides recurring revenue context.

Not every merchant/customer requires subscriptions.

## Schema

| Column | Type | Required | Description |
|---|---|---|---|
| subscription_id | string | Yes | Unique subscription |
| customer_id | string | Yes | Customer reference |
| merchant_id | string | Yes | Merchant reference |
| subscription_start_date | datetime | Yes | Start date |
| subscription_status | string | Yes | active/cancelled/paused |
| recurring_amount | float | Yes | Billing amount |
| billing_frequency | string | Yes | monthly/yearly |
| successful_cycles | integer | No | Successful billing cycles |
| failed_cycles | integer | No | Failed billing cycles |
| next_billing_date | datetime | No | Next payment date |

---

# 10. revenue_events.csv

## Purpose

This is the most important operational input file.

Each row represents an event that requires revenue intelligence.

Examples:

- failed payment
- subscription payment failure
- repeated payment failure
- high churn-risk customer
- abandoned high-value checkout

## Schema

| Column | Type | Required | Description |
|---|---|---|---|
| event_id | string | Yes | Unique event |
| event_timestamp | datetime | Yes | Event time |
| merchant_id | string | Yes | Merchant |
| customer_id | string | Yes | Customer |
| event_type | string | Yes | Event category |
| amount_at_risk | float | Yes | Immediate revenue at risk |
| payment_method | string | No | Payment method |
| failure_reason | string | No | Failure reason |
| attempt_number | integer | No | Current attempt |
| transaction_id | string | No | Related transaction |
| subscription_id | string | No | Related subscription |
| urgency | string | No | low/medium/high |
| event_status | string | Yes | open/resolved/stopped |

## event_type values

Initial MVP:

```text
payment_failed
subscription_payment_failed
repeated_payment_failure
high_value_payment_failure
churn_risk
```

The primary MVP should focus on revenue recovery events. `churn_risk` exists as contextual intelligence, not necessarily as an independent workflow.

---

# 11. intervention_history.csv

## Purpose

Stores previous actions taken by the recovery system.

Used for:

- preventing repeated actions
- calculating attempt counts
- measuring action effectiveness
- agent context
- synthetic ML labels

## Schema

| Column | Type | Required | Description |
|---|---|---|---|
| intervention_id | string | Yes | Unique intervention |
| event_id | string | Yes | Related event |
| customer_id | string | Yes | Customer |
| action_type | string | Yes | Action taken |
| action_timestamp | datetime | Yes | Action time |
| attempt_number | integer | Yes | Attempt number |
| outcome | string | Yes | Result |
| amount_recovered | float | No | Amount recovered |
| response_time_hours | float | No | Time until response |

## action_type values

```text
retry_now
retry_later
payment_link
email
whatsapp
payment_method_update
retention_offer
escalate_to_human
stop_recovery
```

## outcome values

```text
recovered
failed
ignored
pending
escalated
stopped
```

---

# 12. Merchant Configuration

Merchant configuration should initially be a JSON file rather than database records.

Example conceptual fields:

```json
{
  "merchant_id": "MERCHANT_001",
  "max_retry_attempts": 3,
  "max_contact_attempts": 3,
  "contact_cooldown_hours": 24,
  "high_value_escalation_threshold": 50000,
  "low_value_stop_threshold": 100,
  "allowed_actions": [
    "retry_now",
    "retry_later",
    "payment_link",
    "email",
    "whatsapp",
    "payment_method_update",
    "retention_offer",
    "escalate_to_human",
    "stop_recovery"
  ]
}
```

These values should be configurable.

They must not be permanently hardcoded throughout the application.

---

# 13. Canonical Revenue Event

Regardless of the original uploaded schema, the system should normalize data into a canonical event representation.

Conceptually:

```text
CanonicalRevenueEvent
├── event_id
├── merchant_id
├── customer_id
├── event_timestamp
├── event_type
├── amount_at_risk
├── payment_context
├── failure_context
├── attempt_context
├── subscription_context
└── metadata
```

This object becomes the central handoff between:

```text
Data Layer
   ↓
Feature Engineering
   ↓
ML
   ↓
Risk Engine
   ↓
Agents
```

---

# 14. Column Naming and Alias Mapping

Uploaded merchant files may use inconsistent naming.

The ingestion layer should maintain a mapping dictionary.

Examples:

| Uploaded Name | Canonical Name |
|---|---|
| amount | amount_at_risk |
| payment_amount | amount_at_risk |
| transaction_value | amount_at_risk |
| user_id | customer_id |
| customer | customer_id |
| txn_id | transaction_id |
| failure | failure_reason |
| status | transaction_status |

Mapping should be:

1. explicit
2. inspectable
3. logged

The system should never silently guess critical mappings without recording them.

---

# 15. Data Types and Validation

## IDs

All IDs should be stored as strings.

Example:

```text
CUS_000123
TXN_001234
EVT_000321
```

## Currency amounts

- float during MVP
- non-negative
- standardized currency where possible

## Dates

Parse into timezone-aware or consistently interpreted timestamps.

## Boolean

Use true/false internally.

## Categories

Normalize:

```text
"Failed"
"FAILED"
"failed"
```

to:

```text
failed
```

---

# 16. Data Relationships

Primary joins:

```text
revenue_events.customer_id
        ↓
customers.customer_id
```

```text
revenue_events.transaction_id
        ↓
transactions.transaction_id
```

```text
revenue_events.subscription_id
        ↓
subscriptions.subscription_id
```

```text
intervention_history.event_id
        ↓
revenue_events.event_id
```

The pipeline should tolerate missing optional relationships.

Example:

A failed one-time transaction may not have a subscription.

---

# 17. Synthetic Data Generation Strategy

Synthetic data generation is critical.

The goal is not to create random CSVs.

The goal is to create a coherent simulated merchant ecosystem.

Generation order:

```text
Merchant
   ↓
Customers
   ↓
Customer attributes
   ↓
Subscriptions
   ↓
Transactions over time
   ↓
Payment behavior
   ↓
Revenue events
   ↓
Interventions
   ↓
Outcomes
```

Each stage should depend on the previous stages.

---

# 18. Synthetic Customer Generation

Recommended MVP dataset size:

```text
2,000 – 5,000 customers
```

Each customer should receive latent behavioral characteristics.

Example latent variables:

```text
payment_reliability
engagement_level
price_sensitivity
customer_value
churn_tendency
```

These latent variables do not necessarily need to appear directly in exported data.

They can be used internally to generate realistic observed features.

Example:

A highly reliable customer should generally have:

- higher payment success rate
- fewer historical failures
- higher recovery probability

A disengaged customer may have:

- declining activity
- lower engagement
- higher churn tendency

---

# 19. Synthetic Transaction Generation

Recommended:

```text
20,000 – 50,000 transactions
```

depending on development performance.

Transaction generation should depend on customer characteristics.

Example logic:

```text
High reliability customer
→ more successful transactions

Low reliability customer
→ more failed transactions

High value customer
→ larger average transaction amount

Subscription customer
→ recurring transactions
```

Payment failure reasons should not be uniformly random.

Example conceptual tendencies:

```text
network_error
→ often recoverable

payment_timeout
→ often recoverable

card_expired
→ requires payment method update

insufficient_funds
→ retry later may be better

repeated bank decline
→ lower simple retry success
```

This creates meaningful relationships for both ML and action selection.

---

# 20. Synthetic Subscription Generation

Only a subset of customers should have subscriptions.

Recommended:

```text
30% – 50% of customers
```

depending on demo scenario.

Subscription attributes should correlate with customer tenure and value.

Generate:

- monthly plans
- yearly plans
- different recurring amounts
- successful cycles
- failed cycles

Repeated subscription payment failures should increase churn risk.

---

# 21. Synthetic Revenue Event Generation

Revenue events should be derived from transaction history.

Recommended event count:

```text
1,000 – 3,000 events
```

Event generation should identify situations such as:

### Payment failure

```text
transaction_status = failed
```

### Repeated failure

```text
same customer
+
multiple recent failed transactions
```

### High-value failure

```text
failed transaction
+
amount above threshold
```

### Subscription failure

```text
recurring transaction failed
```

### Churn-risk context

```text
declining activity
+
payment failures
+
high churn tendency
```

Events should have varying urgency and value.

---

# 22. Synthetic Intervention History

Intervention history should be generated for a subset of historical events.

Example action-outcome relationships:

| Event Context | More Suitable Action |
|---|---|
| Temporary timeout | retry_now |
| Insufficient funds | retry_later |
| Expired card | payment_method_update |
| Customer inactive | payment_link |
| Repeated failures | escalation |
| High churn/high value | retention_offer |

This relationship must be probabilistic, not deterministic.

A suitable action should have a higher probability of success, but can still fail.

An unsuitable action can occasionally succeed.

This prevents the dataset from becoming unrealistically perfect.

---

# 23. Realistic Correlations

The synthetic generator should intentionally create correlations.

## Recovery probability should generally increase with

- historically reliable customer
- temporary failure reason
- low previous attempts
- prior successful recovery
- recent engagement

## Recovery probability should generally decrease with

- repeated failed attempts
- declining activity
- repeated bank declines
- long inactivity
- multiple ignored interventions

## Churn probability should generally increase with

- declining activity
- repeated failures
- repeated payment friction
- recent ignored recovery actions
- long tenure combined with declining engagement

## Customer value should generally increase with

- total spend
- tenure
- recurring revenue
- successful transaction frequency

These relationships should contain noise.

The goal is plausible patterns, not deterministic formulas that ML models trivially memorize.

---

# 24. Recovery Model Dataset

The recovery model predicts whether a revenue event is eventually recovered.

## Unit of prediction

One historical revenue event.

## Example training row

```text
event_id
amount_at_risk
payment_method
failure_reason
attempt_number
customer_tenure
payment_success_rate
previous_failures
previous_recoveries
engagement_score
activity_trend
...
target_recovered
```

## Target

```text
target_recovered

1 = eventually recovered
0 = not recovered
```

The target should be generated from an underlying probability function plus randomness.

Conceptually:

```text
base probability
+
customer reliability effect
+
failure reason effect
+
engagement effect
-
repeated attempt penalty
+
historical recovery effect
+
noise
```

Clamp final probability:

```text
0.02 ≤ probability ≤ 0.98
```

Then sample the binary outcome.

---

# 25. Churn Model Dataset

The churn model predicts customer churn risk.

## Unit of prediction

One customer snapshot at a point in time.

Features may include:

- tenure
- payment success rate
- previous failures
- failed subscription cycles
- engagement
- activity trend
- customer value
- recent intervention outcomes

## Target

```text
churned

1 = churned
0 = retained
```

Churn labels should be generated from customer behavioral signals.

Example conceptual influences:

```text
declining engagement
+
repeated payment failures
+
failed subscriptions
+
long inactivity
+
ignored recovery attempts
=
higher churn probability
```

---

# 26. Target Label Generation

Synthetic target generation must happen after features/context are generated.

## Wrong approach

```text
Random features
+
Random target
```

This produces no learnable signal.

## Correct approach

```text
Customer behavior
+
Event characteristics
+
Underlying latent tendencies
↓
Probability
↓
Random sampling
↓
Observed outcome
```

Example conceptual recovery function:

```text
recovery_probability =
    base
    + reliability_factor
    + temporary_failure_bonus
    + engagement_bonus
    - repeated_attempt_penalty
    - severe_failure_penalty
    + historical_recovery_bonus
    + random_noise
```

The exact coefficients are implementation details and should be configurable in the generator.

---

# 27. Feature Availability Rules

Avoid data leakage.

A prediction must only use information available at prediction time.

## Recovery model cannot use

- final recovered amount
- final outcome
- future intervention result
- future transaction behavior

## Churn model cannot use

- future cancellation timestamp
- future behavior
- labels disguised as features

Feature engineering should be time-aware where historical timelines are used.

---

# 28. Missing Data Strategy

Synthetic data should intentionally include some missingness.

Real merchant data is incomplete.

Recommended examples:

- missing payment method
- unknown failure reason
- missing engagement score
- missing subscription relationship

Strategies:

## Numeric

- median imputation where appropriate
- explicit missing indicator if useful

## Categorical

```text
unknown
```

## Relationships

Allow optional joins.

The pipeline should not fail because a customer has no subscription.

---

# 29. Class Imbalance Strategy

Real recovery and churn datasets may be imbalanced.

The synthetic dataset should avoid perfectly balanced labels.

Example target ranges:

```text
Recovery success:
30% – 60%
```

depending on event composition.

```text
Churn:
10% – 30%
```

depending on customer population.

Do not force exact ratios if they make the data unrealistic.

During model training:

- inspect class distribution
- use class weights where appropriate
- consider resampling only after establishing a baseline

---

# 30. Train / Validation / Test Strategy

Recommended:

```text
70% Train
15% Validation
15% Test
```

For richer time-series data, prefer temporal splits.

Example:

```text
Older events → training
Middle period → validation
Latest period → testing
```

This is more realistic than random splitting when event timestamps matter.

No leakage should occur across split logic.

---

# 31. Demo Dataset Profiles

The project should eventually support at least three demo scenarios.

## Scenario A — Healthy Merchant

Characteristics:

- high payment success
- low failure rates
- mostly low-priority events

Purpose:

Show that the system does not over-intervene.

## Scenario B — Revenue Leakage Merchant

Characteristics:

- moderate failures
- meaningful recoverable opportunities
- mixed customer quality

Purpose:

Primary demo.

## Scenario C — High Churn Risk Merchant

Characteristics:

- declining engagement
- subscription failures
- repeated payment issues

Purpose:

Demonstrate churn-aware prioritization.

Initial implementation only needs Scenario B.

---

# 32. Data Pipeline

Full data flow:

```text
RAW FILES
   │
   ▼
FILE LOADER
   │
   ▼
COLUMN NORMALIZER
   │
   ▼
SCHEMA VALIDATOR
   │
   ▼
DATA CLEANER
   │
   ▼
CANONICAL TABLES
   │
   ▼
CONTEXT JOINER
   │
   ▼
FEATURE ENGINEERING
   │
   ├──────────────► RECOVERY FEATURES
   │
   └──────────────► CHURN FEATURES
                         │
                         ▼
                    ML MODELS
                         │
                         ▼
                  REVENUE EVENTS
                         │
                         ▼
                    RISK ENGINE
```

---

# 33. Processed Outputs

The data pipeline should create processed artifacts.

```text
data/processed/
├── customers_clean.parquet
├── transactions_clean.parquet
├── revenue_events_clean.parquet
├── recovery_features.parquet
└── churn_features.parquet
```

Parquet is optional.

For smaller MVP datasets CSV is acceptable.

Processed files should be reproducible from raw inputs.

---

# 34. Data Quality Checks

Before analysis, validate:

## Completeness

- required IDs present
- amount present
- event type present

## Validity

- amount >= 0
- valid timestamps
- valid categories

## Uniqueness

- no duplicate primary IDs unless explicitly supported

## Referential integrity

Where possible:

- event customer exists
- transaction exists if referenced
- subscription exists if referenced

Do not reject the entire dataset for every issue.

Return a validation report:

```text
Rows processed
Rows valid
Rows rejected
Warnings
Column mappings applied
Missing value summary
```

---

# 35. Privacy and PII Rules

The MVP should avoid requiring personally identifiable information.

Do not require:

- real names
- phone numbers
- email addresses
- card numbers
- addresses

Use synthetic identifiers.

Communication actions should be simulated.

Example:

```text
customer_id = CUS_00124
```

not:

```text
Rahul Sharma
```

This keeps the demo safer and simplifies data handling.

---

# 36. Data Versioning

Every synthetic generation run should be reproducible.

Store generator metadata:

```text
dataset_version
generation_timestamp
random_seed
customer_count
transaction_count
event_count
```

Example:

```text
data/synthetic/metadata.json
```

The same seed should reproduce equivalent data.

---

# 37. Sample Records

## customers.csv

```csv
customer_id,merchant_id,customer_segment,signup_date,total_orders,total_spend,avg_order_value,payment_success_rate,previous_failures,previous_recoveries,engagement_score,activity_trend,customer_ltv,last_activity_date,churned
CUS_001,MERCHANT_001,HIGH_VALUE,2024-02-15,42,85000,2023.81,0.92,2,1,0.81,stable,125000,2026-08-10,0
CUS_002,MERCHANT_001,AT_RISK,2023-07-10,18,22000,1222.22,0.61,8,1,0.29,declining,28000,2026-07-15,1
```

## transactions.csv

```csv
transaction_id,customer_id,merchant_id,transaction_timestamp,amount,currency,payment_method,transaction_status,failure_reason,attempt_number,subscription_id,is_recurring
TXN_001,CUS_001,MERCHANT_001,2026-08-20T10:30:00,2499,INR,card,success,,1,,false
TXN_002,CUS_002,MERCHANT_001,2026-08-21T09:20:00,1999,INR,card,failed,insufficient_funds,1,SUB_101,true
```

## revenue_events.csv

```csv
event_id,event_timestamp,merchant_id,customer_id,event_type,amount_at_risk,payment_method,failure_reason,attempt_number,transaction_id,subscription_id,urgency,event_status
EVT_001,2026-08-21T09:20:00,MERCHANT_001,CUS_002,subscription_payment_failed,1999,card,insufficient_funds,1,TXN_002,SUB_101,high,open
```

## intervention_history.csv

```csv
intervention_id,event_id,customer_id,action_type,action_timestamp,attempt_number,outcome,amount_recovered,response_time_hours
INT_001,EVT_001,CUS_002,retry_later,2026-08-22T09:30:00,1,recovered,1999,3.5
```

---

# 38. Acceptance Criteria

The data layer is considered complete when:

### File ingestion

- [ ] CSV upload works
- [ ] XLSX upload works
- [ ] invalid files return meaningful errors

### Canonical normalization

- [ ] column aliases map correctly
- [ ] events normalize into internal schema
- [ ] optional relationships are supported

### Synthetic data

- [ ] customers generated
- [ ] transactions generated
- [ ] subscriptions generated
- [ ] revenue events generated
- [ ] intervention history generated
- [ ] dataset is reproducible with seed

### Data quality

- [ ] validation report exists
- [ ] duplicate handling exists
- [ ] missing values handled
- [ ] invalid records identified

### ML readiness

- [ ] recovery features generated
- [ ] churn features generated
- [ ] target labels available
- [ ] no obvious leakage
- [ ] train/test pipeline can be created

---

# Final Data Principle

The quality of the Revenue Recovery Orchestrator depends heavily on the quality of its simulated world.

The synthetic dataset should therefore behave like a simplified but believable revenue ecosystem:

```text
CUSTOMERS
   ↓
BEHAVIOR
   ↓
TRANSACTIONS
   ↓
FAILURES
   ↓
REVENUE EVENTS
   ↓
INTERVENTIONS
   ↓
OUTCOMES
```

The objective is not to create the largest dataset.

The objective is to create a dataset with enough realistic structure that:

- ML can learn meaningful patterns
- the Risk Engine has useful signals
- agents have meaningful context
- actions produce explainable outcomes
- the dashboard tells a believable story

> **Synthetic does not mean random. Synthetic data should contain intentional, explainable relationships that approximate the decision environment the product is designed to solve.**
