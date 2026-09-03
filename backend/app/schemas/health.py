from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["healthy"])
    service: str = Field(examples=["revenue-recovery-orchestrator"])


class AgentHealthResponse(BaseModel):
    configured_mode: str
    llm_available: bool
    provider: str | None = None
    model: str | None = None
    fallback_available: bool = True
    ollama_reachable: bool = False
    ollama_model: str | None = None
    ollama_model_present: bool = False
