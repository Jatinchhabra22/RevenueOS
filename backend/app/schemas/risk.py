from pydantic import BaseModel, Field

from app.schemas.entities import PriorityCategory


class ComponentScores(BaseModel):
    expected_recovery: float = Field(ge=0.0, le=1.0)
    customer_value: float = Field(ge=0.0, le=1.0)
    churn_risk: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    event_id: str
    customer_id: str
    amount_at_risk: float
    recovery_probability: float
    churn_probability: float
    customer_ltv: float | None
    urgency: str
    expected_recovery_value: float
    priority_score: float
    priority_category: PriorityCategory
    component_scores: ComponentScores
    contributing_factors: list[str] = Field(default_factory=list)
