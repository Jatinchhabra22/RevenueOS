from pydantic import BaseModel, Field


class RecoveryPrediction(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    recoverability: str
    model_type: str
    model_version: str
    fallback: bool = False
    contributing_factors: list[str] = Field(default_factory=list)


class ChurnPrediction(BaseModel):
    probability: float = Field(ge=0.0, le=1.0)
    risk_category: str
    model_type: str
    model_version: str
    fallback: bool = False
    contributing_factors: list[str] = Field(default_factory=list)
