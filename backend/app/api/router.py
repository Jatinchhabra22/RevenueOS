from fastapi import APIRouter

from app.api.routes import agent, copilot, data, events, health, metrics, opportunities

api_router = APIRouter()
api_router.include_router(health.router)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router)
v1_router.include_router(data.router)
v1_router.include_router(opportunities.router)
v1_router.include_router(events.router)
v1_router.include_router(agent.router)
v1_router.include_router(copilot.router)
v1_router.include_router(metrics.router)

api_router.include_router(v1_router)
