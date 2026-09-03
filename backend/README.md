# Backend — Revenue Recovery Orchestrator

Thin FastAPI layer over the Python intelligence engine. Route handlers stay thin; domain logic lives in services, ML, risk, agents, guardrails, and tools (later phases).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
pytest
```
