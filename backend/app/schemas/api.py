"""HTTP request/response contracts. Separate from LangGraph internal state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.agent import (
    ActionDecision,
    AgentTraceEvent,
    AuditEntry,
    CandidateAction,
    CustomerAnalysis,
    Diagnosis,
    GuardrailResult,
    InvestigationResult,
    RecoveryOutcome,
    RecoveryStrategy,
    ReflectionResult,
    ToolResult,
)
from app.schemas.entities import Customer, Intervention, RevenueEvent, Subscription, Transaction
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.services.recoverability import RecoverabilityAssessment
from app.schemas.risk import RiskAssessment

PriorityFilter = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class DatasetSummary(BaseModel):
    dataset_id: str
    source: str
    customer_count: int
    transaction_count: int
    subscription_count: int
    revenue_event_count: int
    intervention_count: int
    open_event_count: int
    recovered_event_count: int
    validation_status: Literal["ok", "failed"]
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class OpportunityItem(BaseModel):
    event_id: str
    customer_id: str
    amount_at_risk: float
    recovery_probability: float
    churn_probability: float
    expected_recovery_value: float
    priority_score: float
    priority_category: str
    failure_reason: str | None = None
    payment_method: str | None = None
    event_type: str | None = None
    urgency: str | None = None
    customer_ltv: float | None = None
    status: str | None = None
    recoverability: str | None = None
    pursue: bool | None = None


class OpportunityListResponse(BaseModel):
    items: list[OpportunityItem]
    total: int
    limit: int
    offset: int


class EventDetailResponse(BaseModel):
    event: RevenueEvent
    customer: Customer | None = None
    subscription: Subscription | None = None
    related_transaction: Transaction | None = None
    recent_transactions: list[Transaction] = Field(default_factory=list)
    previous_interventions: list[Intervention] = Field(default_factory=list)
    recovery_prediction: RecoveryPrediction
    churn_prediction: ChurnPrediction
    risk_assessment: RiskAssessment
    recoverability: RecoverabilityAssessment | None = None
    status: str


class AgentRunRequest(BaseModel):
    force_recompute: bool = False
    dry_run: bool = False


class AgentWorkflowResponse(BaseModel):
    workflow_id: str
    event_id: str
    diagnosis: Diagnosis
    recovery_prediction: RecoveryPrediction
    churn_prediction: ChurnPrediction
    risk_assessment: RiskAssessment
    candidate_actions: list[CandidateAction]
    selected_action: CandidateAction
    decision: ActionDecision
    guardrail_result: GuardrailResult
    execution_result: ToolResult | None = None
    outcome: RecoveryOutcome | None = None
    final_decision: str
    status: str
    used_llm: bool = False
    dry_run: bool = False
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    agent_mode: str = "deterministic_fallback"
    provider: str | None = None
    model: str | None = None
    fallback_used: bool = True
    iterations: int = 1
    current_stage: str | None = None
    workflow_status: str | None = None
    terminal_reason: str | None = None
    investigation: InvestigationResult | None = None
    customer_analysis: CustomerAnalysis | None = None
    strategy: RecoveryStrategy | None = None
    reflection: ReflectionResult | None = None
    agent_trace: list[AgentTraceEvent] = Field(default_factory=list)
    iteration_history: list[dict] = Field(default_factory=list)
    llm_call_count: int = 0
    recoverability: RecoverabilityAssessment | None = None


class DatasetMetrics(BaseModel):
    open_event_count: int
    recovered_event_count: int
    revenue_event_count: int


class PriorityBucket(BaseModel):
    priority_category: str
    count: int
    revenue_at_risk: float
    expected_recoverable_revenue: float


class OpportunityMetrics(BaseModel):
    open_opportunities: int
    revenue_at_risk: float
    expected_recoverable_revenue: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    average_recovery_probability: float | None = None
    average_churn_probability: float | None = None
    priority_breakdown: list[PriorityBucket] = Field(default_factory=list)


class AgentExecutionMetrics(BaseModel):
    workflow_count: int
    recovered_outcomes: int
    not_recovered_outcomes: int
    pending_outcomes: int
    blocked_outcomes: int
    no_action_outcomes: int
    simulated_amount_recovered: float


class MetricsOverviewResponse(BaseModel):
    dataset: DatasetMetrics
    opportunities: OpportunityMetrics
    agent_executions: AgentExecutionMetrics


class NamedCountAmount(BaseModel):
    key: str
    count: int
    amount: float = 0.0
    expected_recoverable_value: float = 0.0


class RecoveryFunnel(BaseModel):
    revenue_at_risk: float
    predicted_recoverable_value: float
    revenue_targeted: float | None = None
    actual_recovered: float | None = None
    revenue_targeted_available: bool = False
    actual_recovered_available: bool = False


class PredictedVsActualRow(BaseModel):
    key: str
    predicted_recoverable_value: float = 0.0
    actual_recovered: float = 0.0
    executions: int = 0


class ActionPerformanceRow(BaseModel):
    action_type: str
    observed_recovery_rate: float | None = None
    execution_count: int = 0
    amount_recovered: float = 0.0
    recovered_count: int = 0
    low_sample_size: bool = False
    sample_quality: str = "insufficient"
    confidence_label: str = "Insufficient observations"


class ActivityTrendPoint(BaseModel):
    date: str
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    amount_recovered: float = 0.0


class TopOpportunityChartRow(BaseModel):
    event_id: str
    customer_id: str
    amount_at_risk: float
    expected_recovery_value: float
    priority_score: float
    priority_category: str
    recoverability: str | None = None
    failure_reason: str | None = None


class MetricsDashboardResponse(BaseModel):
    funnel: RecoveryFunnel
    risk_by_level: list[NamedCountAmount] = Field(default_factory=list)
    recoverability: list[NamedCountAmount] = Field(default_factory=list)
    outcomes: list[NamedCountAmount] = Field(default_factory=list)
    failure_reasons: list[NamedCountAmount] = Field(default_factory=list)
    predicted_vs_actual: list[PredictedVsActualRow] = Field(default_factory=list)
    predicted_vs_actual_grouping: str = "priority"
    actions: list[ActionPerformanceRow] = Field(default_factory=list)
    activity_trend: list[ActivityTrendPoint] = Field(default_factory=list)
    activity_trend_available: bool = False
    activity_trend_reason: str | None = None
    top_opportunities: list[TopOpportunityChartRow] = Field(default_factory=list)
    kpis: dict[str, float | int | None] = Field(default_factory=dict)
    disclaimer: str = (
        "Revenue at risk, predicted recoverable value (ERV), and actual recovered amounts are different metrics. "
        "Observed rates are agent workflow outcomes, not dataset labels."
    )


class AgentActivityItem(BaseModel):
    workflow_id: str
    event_id: str
    customer_id: str
    selected_action: str
    guardrail_status: str
    outcome: str | None = None
    execution_status: str | None = None
    timestamp: str | None = None
    amount_recovered: float = 0.0
    dry_run: bool = False
    priority_category: str | None = None
    amount_at_risk: float | None = None
    expected_recovery_value: float | None = None
    agent_mode: str | None = None
    iterations: int | None = None
    provider: str | None = None


class AgentActivityResponse(BaseModel):
    items: list[AgentActivityItem]
    total: int


class CopilotAskRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=800)

    @field_validator("event_id", "question", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class CopilotAskResponse(BaseModel):
    event_id: str
    question: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    fallback_used: bool = True
