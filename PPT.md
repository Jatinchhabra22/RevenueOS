# RevenueOS — PPT Content
### Razorpay AI Buildathon 2026 · Track 03: AI Revenue Recovery

> Use this file as the source of truth for building the presentation on Gamma or any other tool. Each section below is a separate slide or slide group. Suggestions for visuals are in `[brackets]`.

---

## SLIDE 1 — Title Slide

**RevenueOS**

*Agentic Revenue Recovery & Orchestration*

Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery

> Find revenue that's slipping away. Understand why. Win it back.

`[Visual: dark background, minimal wordmark, subtle data-flow lines or a revenue funnel graphic]`

---

## SLIDE 2 — The Problem (Hook)

### Merchants treat every failed payment the same way

```
Payment failed → Retry the same charge
```

That's the entire "recovery strategy" for most businesses.

**What actually happens:**
- Expired cards get retried repeatedly — they will never succeed
- High-value customers get the same treatment as one-time buyers
- Customers get contacted 5 times in 3 days and churn out of frustration
- Recovery "rate" is reported as recovered ÷ total at-risk — which always looks bad
- No one knows if money came back *because* of the action or *despite* it

**The result:**
More retries → more card declines → more customer fatigue → more churn

`[Visual: split screen — left side shows a frustrated customer getting 5 retry emails, right side shows a blank "recovery rate" dashboard]`

---

## SLIDE 3 — The Real Question

### It's not "did the payment fail?"

### It's "what is realistically recoverable — and what should we actually do?"

Three numbers that most platforms confuse:

| | |
|---|---|
| 💸 **Revenue at risk** | The unpaid amount — ₹4,771.66 |
| 🔮 **Expected Recoverable Value (ERV)** | Amount × recovery probability — ₹2,714 |
| ✅ **Actual recovered** | What the agent observed after executing — ₹0 or ₹4,771.66 |

These are **not the same number.** RevenueOS tracks all three separately and never conflates them.

`[Visual: three distinct boxes/columns, each with a different value and a clear label showing they are not equal]`

---

## SLIDE 4 — What is RevenueOS?

### A decision and orchestration layer — not a retry bot

RevenueOS answers:

> **"Which revenue is realistically recoverable, why should we pursue it, and what is the safest, most valuable next action?"**

It separates four jobs that most tools smash together:

| Layer | Job |
|---|---|
| **ML** | What is *likely* to recover? What is the churn risk? |
| **Risk engine** | Is it *worth* pursuing? How many rupees? |
| **Agent (LangGraph)** | What *should* we try? |
| **Guardrails** | What is *allowed* right now? |

The LLM never calculates ERV. The LLM never invents an action. The LLM never bypasses a guardrail.

`[Visual: four-layer stack diagram, each layer with a distinct color and a one-line job description]`

---

## SLIDE 5 — The Build: What We Shipped

### 7 versions. 16 days. One working agentic system.

| Version | Date | What shipped |
|---|---|---|
| **v0.1** | Aug 28 | Project scaffold, data ingestion, ML models, synthetic data generator |
| **v0.2** | Aug 30 | Risk engine — ERV formula, priority scoring, recoverability classification |
| **v0.3** | Aug 31 | Full LangGraph agent graph — supervisor, all nodes, guardrails, simulation |
| **v0.4** | Sep 1 | Workflow persistence, audit trail, Agent Activity page |
| **v0.5** | Sep 2 | Ollama integration, OpenAI-compatible mode, LLM tracing, multi-iteration loop |
| **v0.6** | Sep 3 | Recovery Copilot — read-only LLM explainer on every event |
| **v0.7** | Sep 3 | Recoverability honesty — no-action path, dashboard aggregations, confidence labels |

**Final state:** 173 backend tests passing · Frontend production build clean · Live Ollama (llama3.2:3b) running end-to-end

`[Visual: vertical timeline with version numbers as milestones, each with a one-line description — like a sprint board]`

---

## SLIDE 6 — End-to-End Flow

### From merchant data to measured outcome

```
Merchant CSV / XLSX
        ↓
Validation + canonical event context
        ↓
Recovery & churn prediction (sklearn)
        ↓
Risk engine → ERV + priority score (CRITICAL / HIGH / MEDIUM / LOW)
        ↓
Recoverability classification
        ↓
Ranked opportunity queue
        ↓
LangGraph Agent
  Investigate → Diagnose → Customer analysis
  → Candidate actions (deterministic)
  → Strategy selection (LLM or fallback)
  → Guardrail check (code, not LLM)
  → Simulated execution  —OR—  BLOCK / NO_ACTION
  → Observation → Reflection → back to Supervisor
        ↓
Audit trail + persisted workflow outcome
```

`[Visual: vertical flowchart with the agent section expanded as a loop. Color-code: blue for data/ML, orange for agent, red for guardrails, green for outcome]`

---

## SLIDE 7 — The Agent: LangGraph Graph

### One compiled graph. Supervisor-led. Bounded autonomy.

| Node | Role |
|---|---|
| **Supervisor** | Routes to next step or terminates (wait / escalate / stop / recovered) |
| **Investigator** | Read-only allowlisted tools — 12 tools, zero writes |
| **Diagnosis** | Interprets failure reason + event context |
| **Customer Analyst** | Reads relationship signals, churn signals — does NOT overwrite ML |
| **Strategist** | Picks ONE action from the deterministic candidate list |
| **Guardrail Node** | Policy checks in code — not an LLM |
| **Execution** | Runs the simulated tool |
| **Observer** | Records what happened |
| **Reflection** | Returns: CONTINUE / WAIT / ESCALATE / STOP / RECOVERED |

The supervisor loops on reflection until a terminal reason is reached or `max_iterations` is hit.

**Key constraint:** The strategist must pick from a pre-generated candidate list. Unknown action IDs are rejected. The LLM cannot invent an action that doesn't exist.

`[Visual: node-by-node graph diagram — boxes connected with arrows, with the supervisor at the top routing to everything, and the reflection arrow looping back up]`

---

## SLIDE 8 — Guardrails: The Safety Layer

### The LLM proposes. Code decides.

Every selected action passes through deterministic checks **before any tool runs:**

| Check | What it blocks |
|---|---|
| Merchant allowlist | Actions the merchant hasn't enabled |
| Candidate-list membership | Actions the LLM invented outside the list |
| Event status | Closed / already-recovered events |
| Cooldown window | Same action type within 24 hours |
| Max retries | Exceeded retry limit per event |
| Max contacts | Exceeded contact limit per event |
| Max interventions | Total interventions per event capped at 3 |
| Required inputs | Missing event_id or customer_id |

**`BLOCK` = zero execution tools run.**

No retry, no email, no payment link — nothing. The audit trail records the block reason.

`[Visual: a gate/checkpoint icon with a list of the 8 checks as red/green indicators — like a security scan screen]`

---

## SLIDE 9 — ML + Risk Scoring

### Two models. One formula. Four priority bands.

**Recovery model** — estimates P(recovery) from:
- Payment method, failure reason, attempt count
- Customer tenure, LTV, subscription state
- Historical recovery rate for similar events

**Churn model** — estimates P(churn) from:
- Engagement score, tenure, spend history
- Failed payment count, recovery attempts

**If model files are missing** → documented heuristic fallback runs automatically. `fallback=true` is surfaced in the API response. Nothing silently breaks.

**Priority score formula:**
```
ERV = amount_at_risk × recovery_probability

priority_score (0–100) =
  0.45 × normalize(ERV)
  + 0.25 × normalize(customer LTV)
  + 0.20 × churn_probability
  + 0.10 × urgency_score
```

**Bands:** CRITICAL ≥ 70 · HIGH ≥ 50 · MEDIUM ≥ 30 · LOW < 30

`[Visual: gauge/dial showing 0–100 with CRITICAL/HIGH/MEDIUM/LOW zones, plus the formula broken out as a weighted bar]`

---

## SLIDE 10 — Recoverability: Not Every Event Gets Pursued

### The honest pre-agent filter

Before the agent runs, every event is classified:

| Class | What it means | Action |
|---|---|---|
| `RECOVERABLE` | High probability + adequate ERV | Agent runs |
| `LOW_RECOVERABILITY` | Limited potential; acts if ERV still justifies it | Agent may run |
| `NOT_RECOVERABLE` | Don't send another recovery action | Agent selects `stop_recovery` |
| `ALREADY_RESOLVED` | Event is closed | Guardrail BLOCK |
| `ACTION_BLOCKED` | Cooldown / max attempts hit | Guardrail BLOCK |
| `NEEDS_REVIEW` | Incomplete context | Flagged for human |

**Why this matters:**
Running the agent on every open event wastes contact attempts, fatigues customers, and inflates "recovery rate" by putting low-probability events in the denominator.

`[Visual: funnel — "all open events" at top, narrowing through each class, with only RECOVERABLE + LOW_RECOVERABILITY entering the agent]`

---

## SLIDE 11 — Supported Recovery Actions

### Seven actions. All eligibility is deterministic.

| Action | Intent | Example trigger |
|---|---|---|
| `retry_now` | Immediate retry | Bank declined, network error |
| `retry_later` | Delayed retry / grace window | Insufficient funds |
| `generate_payment_link` | Alternate payment path | Any failure, active customer |
| `send_email` | Low-friction reminder | High-LTV, first failure |
| `payment_method_update` | Replace the instrument | `card_expired` |
| `retention_offer` | Discount / incentive | High-LTV + high-churn |
| `stop_recovery` | Explicit no-action | Low ERV, low probability |

**`card_expired` never gets `retry_now`.** Eligibility is computed from failure reason + merchant policy. The LLM cannot override it.

`[Visual: table with color-coded rows — green for proactive actions, orange for passive, grey for stop_recovery]`

---

## SLIDE 12 — Product: What You Actually See

### 8 pages. Every number comes from the real backend.

| Page | What it shows |
|---|---|
| **Homepage** | Product story and positioning |
| **Overview** | KPI cards, recovery funnel, risk distribution, action performance, ERV vs actual |
| **Opportunities** | Ranked queue filtered by priority and recoverability |
| **Event Detail** | Full context: failure reason, customer, ML scores, ERV, candidate actions, agent result, audit timeline |
| **Run Recovery Agent** | Executes the live LangGraph graph — no fake animation, real API wait |
| **Recovery Copilot** | Ask any question about the event in natural language |
| **Agent Activity** | All persisted workflows with outcome, agent mode, timestamp |
| **Data** | Dataset summary, CSV/XLSX upload |
| **Settings** | Provider health, Ollama reachability, agent mode |

`[Visual: 3×3 grid of page screenshots or wireframe thumbnails]`

---

## SLIDE 13 — Overview Dashboard: Honest Numbers

### The dashboard only shows what it actually knows

**KPI cards (all from live backend aggregations):**
- Total revenue at risk
- Predicted ERV (not the same as above)
- Actual recovered (from persisted workflow outcomes only)
- Observed recovery rate = recovered workflows ÷ (recovered + not recovered)
- Recoverability coverage
- High/critical event count
- No-action (stop_recovery) open events
- Blocked actions

**Charts:**
- Recovery funnel: at risk → predicted ERV → targeted → actual recovered
- Events by risk level (count + amount — separate axes)
- Recoverability distribution
- Action performance with confidence label
- ERV vs actual recovered by event priority
- At-risk amount by failure reason
- Workflow outcomes breakdown

**If a rate is based on fewer than 5 executions** → shows "Low confidence · Limited sample". No fake certainty.

`[Visual: mock dashboard screenshot with the KPI cards across the top and chart grid below — highlight the 3-number distinction prominently]`

---

## SLIDE 14 — Recovery Copilot

### Ask anything about the event. In plain English.

The Recovery Copilot is a **read-only explainer** on the Event Detail page.

- Grounded in that event's verified context + latest workflow JSON
- Powered by Ollama (llama3.2:3b) when available; deterministic fallback when not
- One shared service — works for every event ID
- Cannot run tools, change policy, or access a different event

**Example questions it answers:**
- "Why was this action selected?"
- "Why is this event rated HIGH risk?"
- "Why was the guardrail blocked?"
- "What customer context influenced the decision?"
- "What happened in the last workflow run?"
- "What should happen next?"

`[Visual: chat-style UI mockup showing a question and a grounded answer with specific event data referenced in the response]`

---

## SLIDE 15 — Tech Stack

### Built with production-evolvable choices — no throwaway prototyping

**Backend**
- Python 3.11+ · FastAPI · Uvicorn · Pydantic v2
- LangGraph · LangChain Core
- scikit-learn · Pandas · NumPy · Joblib
- Ollama (llama3.2:3b) · httpx

**Frontend**
- React 19 · Vite · TypeScript
- Tailwind CSS 4 · Recharts · Radix UI · Lucide

**Storage**
- CSV/XLSX file-first datasets
- JSON/JSONL workflow artifacts (atomic writes)
- Joblib model artifacts

**Not used:** PostgreSQL, Redis, Kafka, Docker, vector DB, production auth

**Tests:** 173 pytest tests · Frontend production build via tsc + vite

`[Visual: tech stack icon grid — two columns (backend / frontend), with logos or pill labels for each technology]`

---

## SLIDE 16 — Live Demo Flow

### What you'll see in the product

1. Sign in → `demo@revenueos` / `RevenueOS-Demo`
2. **Overview** — see the three-number distinction: at-risk vs ERV vs actual recovered
3. **Opportunities** — ranked queue, open `EVT_000861` (HIGH priority, ₹4,771.66 at risk)
4. **Event Detail** — card_expired failure, recovery 56.9%, churn 40.9%, ERV ₹2,714, RECOVERABLE
5. **Run recovery agent** → Confirm → real API response (30–60s with Ollama)
   - LLM makes 7 calls: Supervisor → Investigation → Diagnosis → Customer Analysis → Action Selection → Reflection → Supervisor
   - Selected action: `send_email` / `payment_method_update` (depends on run)
   - Guardrail: ALLOW
   - Outcome: RECOVERED ₹4,771.66 or NOT_RECOVERED ₹0 (simulation — both are valid)
   - Audit trail shows every stage
6. **Recovery Copilot** → "Why was this action selected?"
7. **Agent Activity** → same workflow ID as `artifacts/workflows/EVT_000861/`

`[Visual: numbered step flow with small screenshots or wireframes at each step]`

---

## SLIDE 17 — What Makes This Different

### Most "AI recovery" demos are one of two things

❌ A dashboard that shows failed payments

❌ An LLM that says "retry it"

**RevenueOS separates four things they collapse into one:**

| | Typical tool | RevenueOS |
|---|---|---|
| Is it worth pursuing? | Not asked | ERV + recoverability classification |
| What should we try? | Retry | Agent with 7 eligible action types |
| Is this action allowed? | Always yes | Deterministic guardrails in code |
| Did it actually work? | "Recovery rate" | Observed workflow outcomes only |

**Bonus: honest accounting**
- ₹0 recovered is a valid, expected result — not a bug
- A 100% rate on 3 runs shows "Low confidence · Limited sample"
- Predicted ERV is never reported as money recovered

`[Visual: 2-column comparison table, with checkmarks vs X marks — or a "before/after" split slide]`

---

## SLIDE 18 — Limitations (Honest)

### What this MVP is and isn't

**What it is:**
- A complete end-to-end agentic system with real ML, real orchestration, real guardrails
- Testable, reproducible, and explainable at every stage
- A production-evolvable architecture — not throwaway prototype code

**What it isn't (yet):**
- Live Razorpay payment capture or real email/SMS
- Production auth, tenancy, or durable database
- Checkout abandonment or B2B receivables
- Causal effectiveness measurement (outcomes are simulated and observational)
- WhatsApp / voice channels
- Production-monitored ML models

`[Visual: two-column "what it is / what it isn't" with honest icons — checkmark vs coming-soon arrow]`

---

## SLIDE 19 — Roadmap

### Where this goes from here

**Short term**
- Live Razorpay payment retry and refund APIs
- Real email and WhatsApp outreach (Razorpay integrations)
- Promise-to-pay tracking

**Medium term**
- Checkout abandonment event ingestion
- B2B receivables collections workflow
- Merchant policy console with human approval gates
- Streaming ingestion (Kafka / webhooks)

**Long term**
- Production authentication, RBAC, multi-tenancy
- Causal effectiveness modeling (A/B testing per action type)
- Model monitoring and drift detection
- Voice / Hinglish outreach

`[Visual: three-column roadmap (short / medium / long), each with a timeline marker and feature bullets]`

---

## SLIDE 20 — Summary / Close

### RevenueOS in one sentence

> An agentic revenue recovery orchestrator that predicts recoverability, prioritizes revenue opportunities by expected value, selects bounded interventions, and measures actual money recovered — with guardrails and a complete audit trail.

**The three things that make it real:**

1. **Prediction before action** — ML scores every event before anything runs
2. **Bounded autonomy** — the LLM proposes, deterministic code decides
3. **Honest measurement** — revenue at risk ≠ ERV ≠ actual recovered

**Built for Track 03: AI Revenue Recovery**
Razorpay AI Buildathon 2026

`GitHub:` https://github.com/Jatinchhabra22/RevenueOS

`[Visual: closing slide with the one-liner in large text, three bullet points below, and the GitHub link at the bottom]`

---

## APPENDIX A — Key Numbers (for speaker notes)

- **3,000** synthetic customers
- **3,200** revenue events in the demo dataset
- **420** open events available for recovery
- **173** backend tests passing
- **7** LLM calls per full agent run (with Ollama)
- **30–60 seconds** per live graph run on llama3.2:3b
- **12** allowlisted read tools available to the investigator node
- **6** recoverability classes
- **7** supported recovery actions
- **8** guardrail checks per action
- **5** reflection terminal reasons
- **3** max iterations per agent run (configurable)
- **24h** cooldown between same action types (configurable)
- **₹4,771.66** — EVT_000861 amount at risk (demo highlight event)
- **56.9%** — EVT_000861 recovery probability (ML model)
- **₹2,714** — EVT_000861 Expected Recoverable Value

---

## APPENDIX B — Agent State Fields (for technical slides)

Key fields in `AgentState` passed through the graph:

```
event_id, customer_id
event_context        — full EventContext (customer, payment, subscription, interventions)
recovery_prediction  — P(recovery), model_type, fallback flag, contributing factors
churn_prediction     — P(churn), model_type, fallback flag
risk_assessment      — ERV, priority_score, priority_category, contributing_factors
recoverability       — class + pursue flag
candidates           — list of eligible CandidateAction objects
selected_action_id   — picked by strategist node
guardrail_result     — ALLOW or BLOCK + reason codes
execution_result     — simulated outcome
outcome              — RECOVERED / NOT_RECOVERED / PENDING / NO_ACTION / BLOCKED
iteration            — current loop count
agent_mode           — ollama / openai_compatible / deterministic_fallback
audit_trail          — list of AuditEntry (one per node)
agent_trace          — list of AgentTraceEvent (including LLM_CALL events)
```

---

## APPENDIX C — Recoverability Decision Logic

```
Is event already resolved?        → ALREADY_RESOLVED
Max interventions reached?        → ACTION_BLOCKED
Cooldown active?                  → ACTION_BLOCKED
Missing failure reason + customer?→ NEEDS_REVIEW
Very low probability + tiny ERV?  → NOT_RECOVERABLE
ERV below pursue_min (₹100)?      → LOW_RECOVERABILITY (pursue=False)
Low probability but adequate ERV? → LOW_RECOVERABILITY (pursue=True)
Otherwise                         → RECOVERABLE
```

---

## APPENDIX D — Gamma Prompt (paste this to generate the deck)

```
Create a professional presentation for RevenueOS — an agentic revenue recovery 
platform built for the Razorpay AI Buildathon 2026.

Use a dark, modern tech theme with accent colors: deep navy background, 
electric blue and orange highlights, clean sans-serif fonts.

Slides needed (20 total):
1. Title slide
2. The Problem — blind payment recovery
3. The Real Question — three numbers that are not the same
4. What is RevenueOS — four-layer architecture
5. The Build — 7 versions shipped in 16 days
6. End-to-end flow diagram
7. LangGraph agent nodes and roles
8. Guardrails — the safety layer
9. ML + risk scoring formula
10. Recoverability classification
11. Supported recovery actions
12. Product pages overview
13. Overview dashboard and honest metrics
14. Recovery Copilot
15. Tech stack
16. Live demo flow
17. What makes this different — comparison table
18. Limitations (honest)
19. Roadmap
20. Summary and GitHub link

Keep language sharp and confident. No fluff. Use tables and code blocks 
where appropriate. Every claim should be traceable to a real system component.
```
