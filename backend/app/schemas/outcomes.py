"""Outcome intelligence contracts. Agent observations only — not dataset labels."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AGENT_OUTCOME_DISCLAIMER = (
    "These metrics are OBSERVED AGENT OUTCOMES from persisted simulated workflows. "
    "They are not dataset ground-truth labels and are not universal recovery rates."
)

SampleQuality = Literal["insufficient", "low_sample", "sufficient"]
ConfidenceLevel = Literal["low", "medium", "high"]


class OutcomeRecord(BaseModel):
    workflow_id: str
    event_id: str
    customer_id: str | None = None
    action_type: str | None = None
    priority_category: str | None = None
    priority_score: float | None = None
    amount_at_risk: float | None = None
    recovery_probability: float | None = None
    churn_probability: float | None = None
    expected_recovery_value: float | None = None
    outcome: str | None = None
    amount_recovered: float | None = None
    execution_status: str | None = None
    timestamp: str | None = None
    guardrail_status: str | None = None
    failure_reason: str | None = None
    payment_method: str | None = None
    event_type: str | None = None
    customer_ltv: float | None = None
    customer_value_segment: str | None = None
    dry_run: bool = False
    agent_mode: str | None = None
    iterations: int | None = None
    provider: str | None = None


class MetricBreakdownRow(BaseModel):
    key: str
    executions: int
    recovered_count: int
    recovery_rate: float | None = None
    amount_recovered: float = 0.0
    amount_attempted: float = 0.0
    low_sample_size: bool = False


class OutcomeMetricsResponse(BaseModel):
    source: Literal["agent_workflows"] = "agent_workflows"
    disclaimer: str = AGENT_OUTCOME_DISCLAIMER
    executions: int = 0
    successful_recoveries: int = 0
    unsuccessful_recoveries: int = 0
    pending_outcomes: int = 0
    blocked_actions: int = 0
    no_action_outcomes: int = 0
    recovery_rate: float | None = None
    total_amount_recovered: float = 0.0
    total_amount_attempted: float = 0.0
    average_recovered_amount: float | None = None
    expected_recovery_sum: float = 0.0
    observed_recovery_sum: float = 0.0
    missing_amount_recovered_count: int = 0
    top_performing_action: str | None = None
    recovery_by_action_type: list[MetricBreakdownRow] = Field(default_factory=list)
    recovery_by_priority: list[MetricBreakdownRow] = Field(default_factory=list)
    recovery_by_failure_reason: list[MetricBreakdownRow] = Field(default_factory=list)
    recovery_by_payment_method: list[MetricBreakdownRow] = Field(default_factory=list)
    recovery_by_event_type: list[MetricBreakdownRow] = Field(default_factory=list)


class ActionEffectivenessRow(BaseModel):
    action_type: str
    execution_count: int
    recovered_count: int
    recovery_rate: float | None = None
    amount_recovered: float = 0.0
    average_recovered_amount: float | None = None
    average_recovery_probability: float | None = None
    expected_recovery_value: float = 0.0
    observed_recovery: float = 0.0
    observed_vs_expected: float | None = None
    low_sample_size: bool = False
    sample_quality: SampleQuality = "insufficient"


class ActionEffectivenessResponse(BaseModel):
    source: Literal["agent_workflows"] = "agent_workflows"
    disclaimer: str = AGENT_OUTCOME_DISCLAIMER
    items: list[ActionEffectivenessRow] = Field(default_factory=list)


class SegmentRow(BaseModel):
    dimension: str
    segment: str
    action_type: str | None = None
    executions: int
    recovered_count: int
    recovery_rate: float | None = None
    amount_recovered: float = 0.0
    low_sample_size: bool = False


class LearningSignal(BaseModel):
    action_type: str
    segment: str
    segment_dimension: str = "failure_reason"
    observations: int
    observed_recovery_rate: float | None = None
    confidence: ConfidenceLevel = "low"
    sample_quality: SampleQuality = "insufficient"


class SegmentIntelligenceResponse(BaseModel):
    source: Literal["agent_workflows"] = "agent_workflows"
    disclaimer: str = AGENT_OUTCOME_DISCLAIMER
    items: list[SegmentRow] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    learning_signals: list[LearningSignal] = Field(default_factory=list)
