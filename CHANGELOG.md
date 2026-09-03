# Changelog

All notable changes to RevenueOS are documented here.

---

## [0.7.0] — 2026-09-03

### Added
- Recoverability classification with six explicit classes: `RECOVERABLE`, `LOW_RECOVERABILITY`, `NOT_RECOVERABLE`, `ALREADY_RESOLVED`, `ACTION_BLOCKED`, `NEEDS_REVIEW`
- `stop_recovery` action selected automatically when ERV or recovery probability does not justify intervention — the agent now has an honest no-action path
- `GET /api/v1/metrics/dashboard` endpoint with read-only chart aggregations: recoverability distribution, action performance, failure-reason breakdown, ERV vs actual recovered
- Overview page pulls all charts from real backend aggregations, not hardcoded numbers
- Confidence label ("Low confidence · Limited sample") when observed recovery rate is based on fewer than five workflow executions

### Changed
- Overview KPI cards now clearly separate three distinct numbers: revenue at risk, predicted ERV, and actual recovered — they are never conflated
- Guardrail logic unchanged; closed/cooldown/max-attempt events still produce a `BLOCK` regardless of recoverability class

### Fixed
- Backend tests: **173 passed**, 0 failed
- Frontend production build: clean

---

## [0.6.0] — 2026-09-03

### Added
- **Recovery Copilot** on the Event Detail page (`POST /api/v1/copilot/ask`)
- Copilot is read-only: it explains what happened and why, but cannot run tools, modify policy, or access a different event
- Copilot context is assembled from the event's verified detail + the latest persisted workflow JSON
- Ollama path uses the same `invoke_structured` plumbing as the main agent; deterministic fallback returns event-specific facts when the model is unavailable (`fallback_used=true`)
- Unknown event returns `404 EVENT_NOT_FOUND`; empty or malformed question returns `422 INVALID_REQUEST`

### Changed
- Nothing in the agent graph, ML pipeline, risk engine, guardrails, or existing API response contracts was modified in this release

### Fixed
- Backend tests: **157 passed**, 0 failed

---

## [0.5.0] — 2026-09-02

### Added
- Full Ollama integration (`AGENT_MODE=ollama`, `llama3.2:3b`)
- `AGENT_MODE=openai_compatible` for any OpenAI-compatible endpoint via `LLM_API_KEY` + `LLM_BASE_URL`
- `AGENT_MODE=auto` — attaches an OpenAI-compatible LLM if `LLM_API_KEY` is set, otherwise runs deterministic fallback; does not attach Ollama (safe for CI)
- `TracingLLM` wrapper that emits `LLM_CALL_STARTED` / `LLM_CALL_COMPLETED` trace events with schema, agent alias, model name, and duration — no prompts or keys in the trace
- Structured JSON parser: unwraps named envelopes, coerces list/scalar mismatches, validates against Pydantic schema; falls back gracefully on bad JSON without crashing the graph
- Multi-iteration agent loop: reflection result feeds back to the supervisor, which can continue, wait, escalate, stop, or mark as recovered
- `GET /api/v1/agent/health` reporting `configured_mode`, `llm_available`, `provider`, `model`, `fallback_available`, Ollama reachability

### Changed
- Every LangGraph node has an explicit deterministic fallback — an Ollama timeout or invalid JSON response does not abort the workflow
- Strategist must pick `selected_action_id` from the candidate list; IDs not in the list are rejected to fallback, not silently accepted

### Fixed
- `artifacts_path` resolution in the CLI demo script (ML models were loading from the wrong path on some runs)
- Backend tests: **138 passed**, 0 failed

### Notes
- With `llama3.2:3b` on a local Mac, a full graph run typically takes 30–60 seconds and makes 7 LLM calls (Supervisor, Investigation, Diagnosis, Customer Analysis, Action Selection, Reflection, Supervisor)
- The investigation and diagnosis nodes tend to be the slowest (10–25s each)
- Live runs confirm the reflection node consumes the real simulated outcome and routes the supervisor accordingly — it is not cosmetic

---

## [0.4.0] — 2026-09-01

### Added
- Agent Activity page listing all persisted workflows with event ID, outcome, agent mode, and timestamp
- `GET /api/v1/agent/activity` endpoint
- Workflow persistence: `artifacts/workflows/{event_id}/latest.json` and `history.jsonl` (atomic write, append-only history)
- `GET /api/v1/events/{event_id}/agent/latest` and `GET /api/v1/events/{event_id}/agent/{workflow_id}` retrieval endpoints
- Audit timeline on Event Detail showing per-stage results in order

---

## [0.3.0] — 2026-08-31

### Added
- Full LangGraph agent graph (`backend/app/agents/graph.py`): supervisor → investigate → diagnose → customer analysis → candidates → select → guardrails → execute → monitor → reflect → supervisor loop
- Deterministic guardrail checks in code (not LLM): merchant allowlist, candidate-list membership, event-open check, cooldown window, max retries, max contacts, max interventions per event, required-inputs validation
- Candidate generation from failure reason + merchant policy (e.g. `card_expired` never gets `retry_now`)
- `retention_offer` candidate added automatically for high-LTV + high-churn customers
- Hash-seeded simulation engine — outcomes are deterministic per `workflow_id:event_id:action_type` so the same run always replays the same result
- Reflection node with five terminal reasons: `CONTINUE`, `WAIT_FOR_CUSTOMER`, `ESCALATE_TO_MERCHANT`, `STOP_RECOVERY`, `RECOVERED`

---

## [0.2.0] — 2026-08-30

### Added
- Risk engine: ERV = `amount_at_risk × recovery_probability`; priority score 0–100 from weighted ERV, customer LTV, churn probability, and urgency; bands CRITICAL / HIGH / MEDIUM / LOW
- Recoverability classification (pre-agent): determines whether the event should enter the agent at all
- Opportunities endpoint with ranked queue, filtering by risk level and recoverability
- Event Detail API with full `EventContext`: customer, payment, subscription, intervention history, predictions, risk assessment

---

## [0.1.0] — 2026-08-28

### Added
- Initial project structure: FastAPI backend, React + Vite frontend, data pipeline
- CSV/XLSX ingestion with column-alias normalization, cross-table validation, and file upload (`POST /api/v1/data/upload`, 25 MB limit)
- Recovery and churn prediction: sklearn Pipeline + joblib models; heuristic fallback when model artifacts are missing
- Synthetic data generator producing ~3,200 revenue events across 3,000 customers (seeded, reproducible)
- Demo login (`demo@revenueos` / `RevenueOS-Demo`) — browser session flag only, not production auth
- `config/agent_policy.json` and `config/risk_engine.json` for operator-editable policy and scoring weights
