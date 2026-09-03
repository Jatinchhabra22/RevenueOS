"""Structured contracts for the bounded recovery agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ActionType = Literal[
    "retry_now",
    "retry_later",
    "generate_payment_link",
    "send_email",
    "payment_method_update",
    "retention_offer",
    "stop_recovery",
]

GuardrailStatus = Literal["ALLOW", "BLOCK"]
WorkflowStatus = Literal[
    "started",
    "completed",
    "blocked",
    "failed",
    "no_action",
    "waiting",
    "escalated",
]
OutcomeType = Literal[
    "RECOVERED",
    "NOT_RECOVERED",
    "PENDING",
    "BLOCKED",
    "NO_ACTION",
    "WAITING_FOR_CUSTOMER",
    "ESCALATED",
]
SupervisorRoute = Literal[
    "INVESTIGATE",
    "DIAGNOSE",
    "ANALYZE_CUSTOMER",
    "STRATEGIZE",
    "VALIDATE",
    "EXECUTE",
    "OBSERVE",
    "REFLECT",
    "WAIT_FOR_CUSTOMER",
    "ESCALATE_TO_MERCHANT",
    "STOP_RECOVERY",
    "RECOVERED",
]


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    primary_issue: str
    recoverability_reason: str
    churn_concern: str
    customer_context: str
    recommended_strategy: str
    issue_category: str
    event_summary: str
    key_factors: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "fallback"


class CandidateAction(BaseModel):
    action_id: str
    action_type: ActionType
    eligibility: bool = True
    expected_effect: str
    friction: Literal["low", "medium", "high"] = "medium"
    estimated_cost: Literal["none", "low", "medium", "high"] = "low"
    rationale: str
    required_inputs: list[str] = Field(default_factory=list)


class ActionDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selected_action_id: str
    selected_action_type: str = ""
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternative_considered: str | None = None
    source: Literal["llm", "fallback"] = "fallback"
    informed_by_observations: int | None = None
    historical_note: str | None = None


class GuardrailResult(BaseModel):
    allowed: bool
    status: GuardrailStatus
    reason: str
    violations: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    action_id: str
    action_type: str
    execution_id: str
    status: str
    timestamp: datetime
    message: str
    metadata: dict = Field(default_factory=dict)


class RecoveryOutcome(BaseModel):
    outcome: OutcomeType
    action_type: str
    execution_status: str
    amount_recovered: float = 0.0
    remaining_amount_at_risk: float = 0.0
    customer_impact: str
    timestamp: datetime
    explanation: str


class AuditEntry(BaseModel):
    timestamp: datetime
    stage: str
    decision: str
    reason: str
    metadata: dict = Field(default_factory=dict)


class InvestigationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    facts_found: list[str] = Field(default_factory=list)
    important_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    source: Literal["llm", "fallback"] = "fallback"
    tools_used: list[str] = Field(default_factory=list)


class CustomerAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_value_band: str = "unknown"
    churn_risk: str = "unknown"
    relationship_strength: str = "unknown"
    contact_sensitivity: str = "medium"
    recovery_sensitivity: str = "medium"
    recommended_tone: str = "neutral"
    key_customer_signals: list[str] = Field(default_factory=list)
    summary: str = ""
    source: Literal["llm", "fallback"] = "fallback"
    ml_churn_probability: float | None = None


class ActionRankingItem(BaseModel):
    action_id: str
    action_type: str
    score: float = 0.0
    rationale: str = ""


class RecoveryStrategy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    recommended_action: str = ""
    alternative_action: str | None = None
    action_ranking: list[ActionRankingItem] = Field(default_factory=list)
    reasoning_summary: str = ""
    expected_effect: str = ""
    customer_impact: str = ""
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    source: Literal["llm", "fallback"] = "fallback"


class SupervisorDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")
    route: SupervisorRoute
    reason: str
    source: Literal["llm", "fallback"] = "fallback"


class ReflectionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    outcome_interpretation: str = ""
    strategy_assessment: str = ""
    new_information: str = ""
    recommended_next_step: Literal[
        "CONTINUE",
        "WAIT_FOR_CUSTOMER",
        "ESCALATE_TO_MERCHANT",
        "STOP_RECOVERY",
        "RECOVERED",
    ]
    avoid_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    summary: str = ""
    source: Literal["llm", "fallback"] = "fallback"


class AgentTraceEvent(BaseModel):
    trace_id: str
    workflow_id: str
    iteration: int = 1
    agent: str
    event_type: str
    timestamp: datetime
    status: str = "ok"
    summary: str = ""
    tool_name: str | None = None
    decision: str | None = None
    fallback_used: bool = False
    duration_ms: float | None = None

