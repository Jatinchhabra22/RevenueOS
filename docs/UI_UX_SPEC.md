# Revenue Recovery Orchestrator — UI/UX Specification

> **Companion documents:** `PROJECT.md`, `TECHNICAL_SPEC.md`, `DATA_SPEC.md`, `AGENT_SPEC.md`  
> **Purpose:** Define the product experience, information architecture, screens, interactions, visual hierarchy, and demo flow for the Revenue Recovery Orchestrator.

---

# 1. Product Experience Goal

The UI should make a complex AI workflow feel simple.

A merchant should be able to answer three questions within seconds:

1. **How much revenue is currently at risk?**
2. **Which opportunities deserve attention first?**
3. **What is the AI doing to recover that revenue?**

The interface should not feel like:

- a generic admin dashboard
- a chatbot
- an ML notebook
- a table-heavy analytics product

It should feel like an **AI Revenue Operations Command Center**.

---

# 2. Core UX Philosophy

The product experience follows:

```text
SEE
 ↓
UNDERSTAND
 ↓
PRIORITIZE
 ↓
INSPECT
 ↓
TRUST
 ↓
ACT / OBSERVE
```

The UI must surface conclusions before implementation details.

Bad experience:

```text
Upload CSV
↓
See 40 columns
↓
See probabilities
↓
Try to understand what happened
```

Better experience:

```text
₹12.4L Revenue at Risk
↓
₹7.8L Recoverable Opportunity
↓
42 High Priority Events
↓
Inspect top opportunity
↓
See AI decision trail
```

---

# 3. Target User

Primary user:

```text
Merchant / Revenue Operations Team
```

Secondary users:

- finance teams
- payment operations teams
- customer success teams
- internal risk/revenue analysts

For the Buildathon MVP, optimize primarily for a merchant decision-maker seeing the product for the first time.

---

# 4. Product Information Architecture

Recommended navigation:

```text
Dashboard
│
├── Opportunities
│
├── Event Detail
│
├── Agent Activity
│
├── Data & Models
│
└── Settings
```

For MVP, the minimum pages should be:

1. Landing / Upload
2. Main Dashboard
3. Opportunities
4. Event Detail
5. Agent Activity

Settings and Data & Models can be lightweight or secondary.

---

# 5. Primary User Journey

## Step 1 — Enter Product

User sees:

```text
Revenue Recovery Orchestrator
Turn failed payments into prioritized recovery opportunities.
```

Primary CTA:

```text
Upload Revenue Data
```

Secondary option:

```text
Explore Demo Dataset
```

The demo dataset option is important for judges.

---

# 6. Data Upload Experience

The upload screen should not expose unnecessary complexity.

## Main upload card

```text
┌─────────────────────────────────────────────┐
│                                             │
│        Upload Merchant Revenue Data         │
│                                             │
│   Drag & drop CSV or XLSX files here        │
│                                             │
│             [ Choose Files ]                │
│                                             │
│   Supported: Revenue events, transactions,  │
│   customers, subscriptions                  │
│                                             │
└─────────────────────────────────────────────┘
```

Below:

```text
OR

[ Load Demo Merchant Scenario ]
```

---

# 7. Upload Validation Experience

After upload:

```text
Data Processing
```

Show pipeline progress:

```text
✓ Files uploaded
✓ Schema detected
✓ Columns normalized
✓ Data quality checked
○ Building customer context
○ Running predictions
○ Ranking opportunities
```

Avoid fake long loading animations.

Use meaningful status updates from actual backend processing where possible.

---

# 8. Dashboard

The dashboard is the primary product screen.

The first viewport should answer:

```text
What is the revenue problem?
How much can AI potentially recover?
What needs attention?
```

---

# 9. Dashboard Layout

Recommended layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ Logo     Revenue Recovery Orchestrator        Merchant ▼     │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ Sidebar  │   Revenue Intelligence Overview                  │
│          │                                                  │
│          │  [Revenue at Risk] [Recoverable] [Recovered]     │
│          │                                                  │
│          │  ┌────────────────────┐ ┌─────────────────────┐ │
│          │  │ Recovery Pipeline  │ │ Risk Distribution   │ │
│          │  └────────────────────┘ └─────────────────────┘ │
│          │                                                  │
│          │  High Priority Opportunities                     │
│          │  ┌────────────────────────────────────────────┐ │
│          │  │ Event | Customer | Amount | Risk | Action  │ │
│          │  └────────────────────────────────────────────┘ │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

---

# 10. KPI Cards

Top-level KPIs:

## Revenue at Risk

Definition:

```text
Sum of open amount_at_risk
```

## Expected Recoverable Revenue

Definition:

```text
Sum of expected recovery values
```

## Revenue Recovered

Definition:

```text
Sum of successful recovery outcomes
```

## High Priority Opportunities

Definition:

```text
Count of events above priority threshold
```

Optional:

```text
Average Recovery Probability
```

Do not overload the first row with 8–10 metrics.

Four primary cards are enough.

---

# 11. KPI Card Behavior

Each card should include:

- primary value
- concise label
- optional contextual delta
- subtle icon

Example:

```text
₹12.4L
Revenue at Risk

Across 842 active events
```

Avoid meaningless percentage changes unless historical comparison data exists.

---

# 12. Revenue Recovery Funnel

A central visualization should show the revenue journey.

Example:

```text
REVENUE AT RISK
₹12.4L
   ↓
RECOVERABLE OPPORTUNITY
₹8.1L
   ↓
IN ACTIVE RECOVERY
₹4.6L
   ↓
RECOVERED
₹2.8L
```

This is one of the strongest business-oriented visuals.

It explains the product in seconds.

---

# 13. Risk Distribution

Show event distribution by priority:

```text
Critical
High
Medium
Low
```

Recommended visualization:

- stacked bar
- horizontal distribution

The goal is not visual complexity.

The goal is to show:

```text
Where should attention go?
```

---

# 14. Top Opportunities Table

The dashboard should surface the most valuable opportunities.

Columns:

| Field | Description |
|---|---|
| Priority | Critical / High / Medium |
| Event | Event identifier |
| Amount at Risk | Immediate value |
| Recovery Probability | ML output |
| Churn Risk | Context |
| Expected Value | Opportunity |
| AI Action | Selected action |
| Status | Workflow status |

Sort default:

```text
Highest priority / expected value first
```

Clicking a row opens Event Detail.

---

# 15. Opportunities Page

This page is the operational queue.

Layout:

```text
OPPORTUNITIES
842 active events

[ Search ]

[Priority ▼] [Event Type ▼] [Status ▼] [Action ▼]

--------------------------------------------------------

Critical Opportunities

Event     Amount      Recovery    Churn     AI Action
EVT-102   ₹48,000     72%         68%       Escalate
EVT-219   ₹25,000     81%         22%       Retry Later
...
```

---

# 16. Opportunity Prioritization UX

Priority should never appear as a mysterious score alone.

Show:

```text
HIGH PRIORITY
```

with expandable explanation:

```text
Why this matters:
• ₹48,000 immediate revenue at risk
• 72% estimated recovery probability
• High customer lifetime value
• Elevated churn risk
```

This is crucial for explainability.

---

# 17. Event Detail Page

This is the most important deep-dive screen.

The user should understand one event completely.

Recommended structure:

```text
EVENT EVT-102
High Priority

₹48,000
Revenue at Risk

[Overview] [AI Reasoning] [Actions] [History]
```

---

# 18. Event Overview

Display:

### Event Information

```text
Event Type
Payment Failure

Failure Reason
Insufficient Funds

Attempt
1 of 3

Payment Method
Card
```

### Customer Context

```text
Customer Segment
High Value

Tenure
18 months

Historical Payment Success
93%

Customer LTV
₹1,20,000
```

### Intelligence

```text
Recovery Probability
78%

Churn Probability
41%

Expected Recovery Value
₹37,440

Priority
HIGH
```

---

# 19. AI Decision Panel

This panel should clearly show the AI's decision.

Example:

```text
AI RECOMMENDATION

Retry Payment Later

Confidence Context:
High historical payment reliability and a temporary
failure pattern suggest that a delayed retry is the
lowest-friction recovery option.

Alternative considered:
Generate Payment Link
```

Important:

Do not call everything "confidence" if it is not a mathematically calibrated confidence score.

Use terms carefully.

---

# 19A. Ask Recovery Copilot

The Event Detail page includes a **Ask Recovery Copilot** section. It is a read-only explanation panel for the currently open event.

- The event ID comes from the route. The user never types it.
- Quick questions (selected action, high risk, blocked action, execution, next step) submit against that event.
- Answers are grounded in that event’s context (ML, risk, latest workflow if present).
- Label it **Read-only explanation** / based on this event's workflow context. Do not imply the Copilot is running a recovery action.
- Show provider/model and an honest fallback badge when the deterministic explainer was used.

---

# 20. Candidate Action Comparison

A powerful feature for the demo:

```text
ACTION OPTIONS

✓ Retry Later
Best balance of recovery potential and low friction

Payment Link
Useful fallback if retry fails

Escalate
Not currently required
```

This visually proves that the AI did not randomly output one action.

It evaluated bounded options.

---

# 21. Agent Reasoning Timeline

The Event Detail page should include a visual execution timeline.

Example:

```text
10:00:01
Context assembled
Customer history and transaction behavior loaded

↓

10:00:02
Recovery prediction
Estimated recovery probability: 78%

↓

10:00:03
Churn assessment
Moderate churn risk detected

↓

10:00:04
Revenue prioritized
Expected recovery value: ₹37,440

↓

10:00:05
Action candidates generated
Retry Later, Payment Link

↓

10:00:06
AI selected
Retry Later

↓

10:00:06
Guardrail check
Approved

↓

10:00:07
Action executed
Retry scheduled
```

This is probably one of the strongest Buildathon demo features.

---

# 22. Agent Activity Page

This page gives a system-level view.

Header:

```text
AI Recovery Activity
```

Metrics:

```text
Active Workflows
Successful Recoveries
Escalations
Stopped Workflows
```

Below:

```text
LIVE / RECENT AGENT ACTIVITY
```

Timeline feed:

```text
EVT-102
Recovery agent selected retry_later

EVT-219
High-value customer escalated

EVT-311
Payment successfully recovered

EVT-455
Recovery stopped after policy limit
```

For the MVP, "live" can mean periodically refreshed simulation status.

Do not fake real-time complexity if not implemented.

---

# 23. Workflow Visualization

For selected events, visualize the agent graph.

```text
Event
  ↓
Diagnosis
  ↓
Predictions
  ↓
Risk Assessment
  ↓
Action Selection
  ↓
Guardrails
  ↓
Execution
  ↓
Outcome
```

Current node should be visually identifiable.

This directly communicates the agentic architecture to judges.

---

# 24. Data & Models Page

Optional but useful.

Purpose:

Show technical credibility without overwhelming primary users.

Sections:

### Dataset Summary

```text
Customers: 5,000
Transactions: 40,000
Revenue Events: 2,100
```

### Model Performance

```text
Recovery Model
ROC-AUC: X.XX

Churn Model
ROC-AUC: X.XX
```

Only show real metrics.

Never hardcode impressive numbers.

### Feature Importance

Optional simple chart.

Keep this page secondary.

---

# 25. Settings / Policy Page

Optional MVP-lite page.

Show merchant policy:

```text
Maximum Retry Attempts: 3
Contact Cooldown: 24 hours
High Value Threshold: ₹50,000
Allowed Actions: 8
```

This reinforces:

```text
AI autonomy is policy-bounded.
```

Judges may appreciate this product maturity.

---

# 26. Empty States

The UI should handle empty data gracefully.

Example:

```text
No revenue events yet

Upload merchant data or load a demo scenario
to identify recovery opportunities.
```

Never show broken blank tables.

---

# 27. Error States

Examples:

### Invalid file

```text
We couldn't detect the required event fields.

Required:
• Customer identifier
• Event timestamp
• Amount
• Event type
```

### Processing failure

```text
Analysis could not be completed.

[Retry Processing]
[View Details]
```

Technical stack traces should not be exposed in the main UI.

---

# 28. Loading States

Use skeletons for:

- KPI cards
- tables
- charts

For longer processing:

```text
Analyzing 2,184 revenue events...

✓ Data normalized
✓ Features generated
✓ Recovery predictions complete
○ Prioritizing opportunities
```

Progress should map to actual pipeline stages.

---

# 29. Visual Design Direction

The design should feel:

- premium
- technical
- calm
- operational
- intelligent

Avoid:

- excessive gradients
- neon cyberpunk aesthetics
- too many glowing elements
- random AI brain imagery
- excessive animated backgrounds

Preferred direction:

```text
Modern fintech
+
Enterprise AI
+
Clean analytics
```

---

# 30. Color Philosophy

Use a restrained palette.

Semantic colors:

```text
Critical → danger emphasis
High → warning emphasis
Medium → attention
Low → neutral
Success → positive
```

Do not assign semantic meaning inconsistently.

The overall interface should remain mostly neutral with one primary accent.

---

# 31. Typography

Priorities:

1. readability
2. hierarchy
3. numerical clarity

Large numbers should be easy to scan.

Examples:

```text
₹12.4L
```

should visually dominate:

```text
Revenue at Risk
```

Use consistent formatting for:

- currency
- percentages
- dates
- IDs

---

# 32. Component System

Recommended reusable components:

```text
AppShell
Sidebar
Topbar
MetricCard
SectionHeader
PriorityBadge
StatusBadge
ProbabilityIndicator
OpportunityTable
FilterBar
EventSummaryCard
CustomerContextCard
DecisionCard
CandidateActionCard
AgentTimeline
WorkflowGraph
EmptyState
ErrorState
UploadZone
```

Do not build every screen as independent one-off JSX.

---

# 33. Priority Badge System

Priority values:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

The badge should be visually consistent across:

- dashboard
- tables
- event details
- activity feed

Avoid showing only raw scores such as:

```text
0.8372
```

to the primary user.

Raw score can appear in technical detail if needed.

---

# 34. Probability Display

Avoid over-precision.

Bad:

```text
0.783941
```

Good:

```text
78%
```

Optional technical detail:

```text
Recovery probability: 0.784
```

should only appear in debug/model views.

---

# 35. Currency Formatting

Indian context is relevant for the Buildathon.

Support:

```text
₹12,500
₹1.2L
₹12.4L
₹1.2Cr
```

Internally store full numeric values.

Display formatting is presentation logic.

---

# 36. Dashboard Chart Guidelines

Recommended charts:

## Revenue Funnel

Purpose:

```text
Where is revenue moving?
```

## Priority Distribution

Purpose:

```text
How many events need attention?
```

## Recovery Outcomes

Purpose:

```text
Is the system working?
```

## Opportunity Value Ranking

Purpose:

```text
What should we focus on?
```

Avoid charts merely because a dashboard "needs charts."

Every visualization should answer a decision question.

---

# 37. Interaction Principles

## Click event

Open deep context.

## Hover chart

Show precise values.

## Click priority

Filter opportunities.

## Click agent workflow

Open event detail.

## Click candidate action

Show why it was considered.

Interactions should reveal depth progressively.

Do not put all information on the dashboard simultaneously.

---

# 38. Explainability UX

Every important AI decision should answer:

```text
What happened?
Why does it matter?
What did the system predict?
What action was selected?
Why was that action selected?
What happened next?
```

This is the explainability framework for the UI.

---

# 39. Trust Indicators

The product should visually communicate boundaries.

Examples:

```text
✓ Policy Validated
```

```text
✓ Action within retry limit
```

```text
⚠ Human review required
```

This makes the system feel controlled rather than black-box autonomous.

---

# 40. Demo Mode

The application should have a dedicated demo flow.

Recommended entry CTA:

```text
Explore Demo Scenario
```

Demo dataset should load immediately.

After loading:

```text
Scenario: Revenue Leakage Merchant

2,184 events analyzed
₹12.4L revenue at risk
₹8.1L estimated recoverable opportunity
```

This prevents judges from needing to upload files.

---

# 41. Demo Narrative

The UI should support this story:

### Scene 1

```text
Merchant has ₹12.4L revenue at risk.
```

### Scene 2

```text
The system identifies ₹8.1L as potentially recoverable.
```

### Scene 3

```text
Opportunities are prioritized by expected value and customer risk.
```

### Scene 4

```text
We inspect a high-value payment failure.
```

### Scene 5

```text
The AI agent diagnoses the situation and evaluates valid actions.
```

### Scene 6

```text
A guardrail validates the decision.
```

### Scene 7

```text
The action is executed and the outcome feeds back into the system.
```

The UI is part of the pitch.

---

# 42. Recommended MVP Screens

## Screen 1

### Landing / Upload

Goal:

```text
Get data into system quickly.
```

## Screen 2

### Dashboard

Goal:

```text
Understand revenue opportunity.
```

## Screen 3

### Opportunities

Goal:

```text
Prioritize work.
```

## Screen 4

### Event Detail

Goal:

```text
Understand and trust AI decisions.
```

## Screen 5

### Agent Activity

Goal:

```text
Demonstrate autonomous workflows.
```

These five screens are sufficient for a strong MVP.

---

# 43. What NOT to Build Initially

Avoid wasting time on:

- authentication
- multi-user teams
- complex notification systems
- profile pages
- billing
- full merchant onboarding
- complex settings
- dark/light theme switching
- dozens of dashboard pages
- real-time WebSockets unless necessary

The Buildathon goal is product depth, not SaaS completeness.

---

# 44. Responsive Strategy

Primary optimization:

```text
Desktop
```

Reason:

- judges likely view demo on laptop
- analytics dashboard benefits from width
- complex event detail is easier to inspect

Tablet should degrade reasonably.

Mobile can be limited but should not be completely broken.

Do not spend significant MVP time on perfect mobile responsiveness.

---

# 45. Accessibility Baseline

Ensure:

- readable contrast
- semantic button labels
- keyboard-accessible major controls
- status not communicated only by color
- readable font sizes

No need to over-engineer accessibility systems for MVP, but basic standards should be respected.

---

# 46. UI State Management

Frontend state categories:

## Server state

- uploaded datasets
- event results
- workflow details
- analytics

## Local UI state

- filters
- selected event
- expanded panels
- active tabs

Avoid unnecessary global state.

Use the simplest architecture compatible with the chosen frontend stack.

---

# 47. API Interaction UX

Recommended frontend flow:

```text
Upload
 ↓
POST /analyze
 ↓
Processing state
 ↓
Receive analysis summary
 ↓
Render dashboard
```

For event inspection:

```text
Click Event
 ↓
GET /events/{id}
 ↓
Render detail
```

For agent workflow:

```text
POST /events/{id}/run-agent
 ↓
Workflow status
 ↓
Render timeline
```

Exact endpoint names can evolve according to `TECHNICAL_SPEC.md`.

---

# 48. Microcopy Tone

Tone should be:

- clear
- operational
- confident
- non-hype

Avoid:

```text
Our revolutionary AI super-agent has detected...
```

Prefer:

```text
Recovery opportunity identified.
```

Avoid vague:

```text
AI magic is happening...
```

Prefer:

```text
Analyzing payment history and intervention context.
```

---

# 49. Suggested Page Hierarchy

```text
Revenue Recovery Orchestrator
│
├── Dashboard
│   ├── KPIs
│   ├── Revenue Funnel
│   ├── Risk Distribution
│   └── Top Opportunities
│
├── Opportunities
│   ├── Filters
│   └── Ranked Events
│
├── Event Detail
│   ├── Overview
│   ├── Customer Context
│   ├── Predictions
│   ├── AI Decision
│   ├── Candidate Actions
│   └── Agent Timeline
│
├── Agent Activity
│   ├── Workflow Metrics
│   ├── Activity Feed
│   └── Workflow Inspector
│
└── Data & Models
    ├── Dataset Summary
    └── Model Metrics
```

---

# 50. MVP Acceptance Criteria

The UI/UX layer is complete when:

### Upload

- [ ] CSV upload works
- [ ] XLSX upload works
- [ ] demo dataset can load
- [ ] validation errors are understandable

### Dashboard

- [ ] revenue KPIs visible
- [ ] revenue funnel visible
- [ ] risk distribution visible
- [ ] top opportunities visible

### Opportunities

- [ ] events are sortable/filterable
- [ ] priority is understandable
- [ ] event opens detail page

### Event Detail

- [ ] event context visible
- [ ] customer context visible
- [ ] predictions visible
- [ ] selected action visible
- [ ] reasoning visible
- [ ] agent timeline visible

### Agent Activity

- [ ] workflow statuses visible
- [ ] recent activity visible
- [ ] outcomes visible

### Product Experience

- [ ] primary insight visible within first viewport
- [ ] no unnecessary complexity
- [ ] demo flow understandable without explanation

---

# Final UX Principle

The UI should make the project understandable even before the technical architecture is explained.

A judge should be able to look at the product and immediately understand:

```text
There is revenue at risk.
      ↓
The system predicts which opportunities matter.
      ↓
AI reasons about valid recovery actions.
      ↓
Guardrails control execution.
      ↓
Outcomes are monitored and logged.
```

The interface should therefore prioritize:

> **Business clarity first. AI transparency second. Technical depth on demand.**

The best UI is not the one with the most charts.

It is the one that makes the product's intelligence and business value obvious in under a minute.
