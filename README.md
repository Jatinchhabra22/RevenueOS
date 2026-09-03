# RevenueOS

AI-powered revenue recovery and orchestration platform built for the Razorpay AI Buildathon 2026 (Track 03 — AI Revenue Recovery).

RevenueOS is a decision and orchestration layer for failed payments and at-risk subscriptions. It is not a retry bot, not a generic chatbot, and not a static BI dashboard.

---

## The problem

Most merchants treat a failed payment as: *payment failed → retry the same charge*. That's cheap to automate and expensive in practice.

Blind recovery retries on expired cards, ignores customer value, ignores churn risk, has no cooldown, and can't distinguish between money that *might* come back and money that *did* come back.

Common failure modes:
- Retrying instruments that can't succeed (expired card, bank-blocked instrument)
- Wasting contact attempts on low-value, low-probability events
- Fatiguing customers who've already failed multiple times
- FIFO queues instead of expected-rupee prioritization
- No customer or subscription context in the decision
- No stopping rule when intervention is no longer justified
- "Recovery rate" calculated against total at-risk amount — which always overstates success

RevenueOS answers a different question: **which revenue is realistically recoverable, why should we pursue it, and what's the safest and most valuable next action?**

---

## How it works

```
Merchant CSV / XLSX
        ↓
Validation + canonical event context
        ↓
Recovery & churn prediction (sklearn models)
        ↓
Risk engine — ERV + priority score
        ↓
Recoverability classification
        ↓
Ranked opportunity queue
        ↓
LangGraph agent
  → Investigate → Diagnose → Customer analysis
  → Candidate actions (deterministic)
  → Strategy selection
  → Guardrail check (deterministic, in code)
  → Simulated execution  —or—  BLOCK / NO_ACTION
  → Observation → Reflection → back to Supervisor
        ↓
Audit trail + persisted workflow outcome
```

A few things worth calling out explicitly:

**ERV is not money recovered.** `Expected Recoverable Value = amount × recovery_probability`. These are three separate numbers and the product keeps them separate:

```
Revenue at risk  ≠  Predicted ERV  ≠  Actual recovered
```

**Not every event deserves a recovery attempt.** Before anything runs, each event is classified into one of: `RECOVERABLE`, `LOW_RECOVERABILITY`, `NOT_RECOVERABLE`, `ALREADY_RESOLVED`, `ACTION_BLOCKED`, or `NEEDS_REVIEW`. When intervention isn't economically justified the agent selects `stop_recovery` rather than blindly acting.

**The LLM doesn't control guardrails.** Policy checks run in deterministic code (`backend/app/agents/guardrails.py`). BLOCK means zero execution tools run, regardless of what any model says.

---

## Agent architecture

Orchestration is LangGraph — one compiled graph, supervisor-led, with structured typed state.

| Node | What it does |
|---|---|
| Supervisor | Routes to the next step or terminates (wait / escalate / stop / recovered) |
| Investigator | Calls read-only allowlisted tools; no writes |
| Diagnosis | Interprets the failure reason and event context |
| Customer analyst | Reads relationship and churn signals |
| Strategist | Picks one `selected_action_id` from the deterministic candidate list |
| Guardrail node | Policy checks in code — not an LLM |
| Execution | Runs the simulated tool |
| Observer | Records outcome and remaining at-risk amount |
| Reflection | Returns CONTINUE, WAIT_FOR_CUSTOMER, ESCALATE_TO_MERCHANT, STOP_RECOVERY, or RECOVERED to the supervisor |

LLM provider is Ollama (`llama3.2:3b`) when `AGENT_MODE=ollama`. If the model is unreachable, times out, or returns invalid JSON, deterministic fallback takes over within the same graph — the workflow doesn't abort. `AGENT_MODE=auto` doesn't attach Ollama so it's safe for tests and CI.

---

## Recoverability classes

| Class | Meaning |
|---|---|
| `RECOVERABLE` | Worth pursuing |
| `LOW_RECOVERABILITY` | Limited potential; may still act if ERV is high enough |
| `NOT_RECOVERABLE` | Don't send another recovery action |
| `ALREADY_RESOLVED` | Event is closed or already recovered |
| `ACTION_BLOCKED` | Policy would block any new action (cooldown, max attempts) |
| `NEEDS_REVIEW` | Context is too incomplete for automated action |

---

## Supported actions

Eligibility is deterministic — derived from failure reason + merchant policy. For example, `card_expired` never gets `retry_now`.

| Action | Intent |
|---|---|
| `retry_now` | Immediate retry of the same instrument |
| `retry_later` | Delayed retry / grace window |
| `generate_payment_link` | Alternate payment path |
| `send_email` | Low-friction reminder |
| `payment_method_update` | Replace the instrument |
| `retention_offer` | High-LTV + high-churn situations |
| `stop_recovery` | Explicit no-action / stop |

All tools are simulated. No live Razorpay charges, no real email. Outcomes are hash-seeded per `workflow_id:event_id:action_type` so replays are deterministic.

---

## ML and risk scoring

**Recovery model** — estimates P(recovery) from payment, attempt, failure-reason, and customer features. Falls back to a documented failure-reason heuristic if model artifacts are missing (`fallback=true` in the response).

**Churn model** — estimates P(churn) from engagement, tenure, spend, and related customer features. Same artifact/fallback pattern.

**Priority score (0–100)**:
```
ERV = amount_at_risk × recovery_probability

priority_score =
  0.45 × normalize(ERV, ref=₹5000)
  + 0.25 × normalize(customer_ltv, ref=₹200000)
  + 0.20 × churn_probability
  + 0.10 × urgency_score
```

Bands: CRITICAL ≥ 70, HIGH ≥ 50, MEDIUM ≥ 30, else LOW. Weights and thresholds are in `config/risk_engine.json`.

---

## Tech stack

**Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Pandas, NumPy, scikit-learn, LangGraph, LangChain Core, httpx, Ollama

**Frontend**: React 19, Vite, TypeScript, Tailwind CSS 4, Recharts, Radix UI Slot, Lucide

**Storage**: Local files — CSV/XLSX datasets, JSON/JSONL workflow artifacts, joblib model artifacts

Not used: PostgreSQL, Redis, Kafka, Docker, vector DB, production auth.

---

## Pages

| Page | Route | Purpose |
|---|---|---|
| Homepage | `/` | Product overview |
| Login | `/login` | Demo session (`demo@revenueos` / `RevenueOS-Demo`) |
| Overview | `/app` | Revenue intelligence charts and KPIs |
| Opportunities | `/app/opportunities` | Ranked recovery queue |
| Event detail | `/app/events/:eventId` | Full context + run agent + Recovery Copilot |
| Agent Activity | `/app/activity` | Persisted workflow history |
| Data | `/app/data` | Dataset summary and upload |
| Settings | `/app/settings` | Provider health and agent mode |

---

## API

All routes under `/api/v1` unless noted.

| Group | Method | Path |
|---|---|---|
| Health | GET | `/health`, `/api/v1/health` |
| Agent health | GET | `/api/v1/agent/health` |
| Data | GET | `/api/v1/data/summary` |
| Data | POST | `/api/v1/data/upload` |
| Opportunities | GET | `/api/v1/opportunities` |
| Events | GET | `/api/v1/events/{event_id}` |
| Agent run | POST | `/api/v1/events/{event_id}/agent/run` |
| Agent result | GET | `/api/v1/events/{event_id}/agent/latest` |
| Agent result | GET | `/api/v1/events/{event_id}/agent/{workflow_id}` |
| Activity | GET | `/api/v1/agent/activity` |
| Metrics | GET | `/api/v1/metrics/overview` |
| Metrics | GET | `/api/v1/metrics/dashboard` |
| Outcomes | GET | `/api/v1/metrics/outcomes` |
| Actions | GET | `/api/v1/metrics/actions` |
| Copilot | POST | `/api/v1/copilot/ask` |

Interactive docs at http://localhost:8000/docs once the backend is running.

---

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Ollama (optional — only needed for local LLM)

### Clone and configure

```bash
git clone https://github.com/Jatinchhabra22/RevenueOS.git
cd RevenueOS
cp .env.example .env
```

Key variables in `.env`:

| Variable | Default | Notes |
|---|---|---|
| `AGENT_MODE` | `auto` | `auto`, `ollama`, `deterministic_fallback`, `openai_compatible` |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS for the frontend |
| `DATA_DIR` | `data/demo` | Path to the active dataset folder |
| `ARTIFACTS_DIR` | `artifacts` | Models and workflow JSON |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Only needed for `AGENT_MODE=ollama` |
| `OLLAMA_MODEL` | `llama3.2:3b` | Only needed for `AGENT_MODE=ollama` |
| `LLM_API_KEY` | — | Only for `openai_compatible` / `auto` with a key |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend → backend |

### Generate demo data and train models

Model artifacts are gitignored so you need to generate them after cloning:

```bash
python scripts/generate_synthetic_data.py --seed 42 --customers 3000
python scripts/train_models.py --data-dir data/demo --seed 42
```

This creates ~3,200 revenue events across 3,000 customers. The top open HIGH opportunity in a seed-42 run is `EVT_000861`.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173

### Ollama (optional)

```bash
ollama serve
ollama pull llama3.2:3b
```

Set `AGENT_MODE=ollama` in `.env` and restart the backend. If Ollama goes down mid-demo, setting `AGENT_MODE=deterministic_fallback` keeps everything working — health stays green, workflows complete, you just won't see LLM trace calls.

---

## Demo walkthrough

1. http://localhost:5173 → sign in with `demo@revenueos` / `RevenueOS-Demo`
2. **Overview** — at-risk vs ERV vs actual recovered, recoverability distribution
3. **Opportunities** — ranked queue by priority score; open `EVT_000861`
4. **Event detail** — failure reason, customer context, recovery/churn probabilities, ERV, recoverability class
5. **Run recovery agent** → Confirm → wait for the real API response (~30–60s with Llama 3.2 3B)
6. Review the audit trail: selected action, guardrail result, execution outcome, reflection
7. **Ask Recovery Copilot** — "Why was this action selected?" or "Why is this event HIGH risk?"
8. **Agent Activity** — workflow IDs match `artifacts/workflows/`

CLI alternative:

```bash
python scripts/reset_demo.py --clear-workflows
python scripts/run_agentic_demo.py --agent-mode ollama --event-id EVT_000861
# or without Ollama:
python scripts/run_agentic_demo.py --agent-mode deterministic_fallback --event-id EVT_000861
```

Clear workflows before re-running — simulated interventions count toward cooldowns and max-intervention limits.

---

## Testing

```bash
cd backend && source .venv/bin/activate && pytest
cd frontend && npm run build
```

Live Ollama tests (require `llama3.2:3b` running locally):

```bash
cd backend && pytest -m ollama
```

Default `pytest` doesn't require Ollama. Latest passing: **173 tests**, frontend build clean.

---

## Limitations

This is a buildathon MVP, not a production platform.

- Synthetic demo data (real uploads supported via the Data page)
- All payment and messaging tools are simulated — no live Razorpay charges or real email
- `llama3.2:3b` is slow on a local machine; invalid JSON responses fall back gracefully per node
- sklearn baselines, not production-monitored models
- Observed action effectiveness is descriptive of simulation outcomes, not causal
- Demo login is a browser-local session flag, not SSO or RBAC
- File-first storage (CSV + JSON), no production database
- Policy JSON is edited manually by operators; the agent cannot modify it

---

## Roadmap

- Live Razorpay payment and refund APIs
- Checkout abandonment and B2B receivables ingestion
- Promise-to-pay tracking
- WhatsApp / voice outreach
- Merchant policy console with human approval workflows
- Streaming ingestion
- Production auth, tenancy, and durable storage

---

## Repository layout

```
RevenueOS/
├── backend/          FastAPI app, LangGraph agent, ML, tests
│   ├── app/
│   └── tests/
├── frontend/         React + Vite merchant console
│   └── src/
├── config/           agent_policy.json, risk_engine.json
├── data/             File-first datasets (demo data gitignored)
├── artifacts/        Model files + workflow JSON (joblib gitignored)
├── scripts/          Data generation, model training, demo scripts
└── docs/             Architecture and spec documents
```

---

See [`CHANGELOG.md`](CHANGELOG.md) for version history and [`docs/`](docs/) for architecture and spec documents.
