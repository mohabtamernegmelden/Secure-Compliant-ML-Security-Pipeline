from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import sanitize_input_text


class PredictionInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "age": 35,
                "income": 75000.0,
                "transaction_amount": 120.5,
                "risk_score": 0.23,
                "department": "finance",
                "user_role": "user",
            }
        },
    )

    age: int = Field(..., ge=18, le=120, description="Age of the entity or user")
    income: float = Field(..., ge=0.0, le=10000000.0, description="Annual income of the entity or user")
    transaction_amount: float = Field(..., ge=0.0, le=5000000.0, description="Transaction amount being evaluated")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Pre-calculated risk score for the request")
    department: Literal["finance", "healthcare", "other"] = Field(..., description="Department originating the request")
    user_role: Literal["admin", "analyst", "user"] = Field(..., description="Role of the user making the transaction")

    @field_validator("department", "user_role")
    @classmethod
    def sanitize_string_fields(cls, v: str) -> str:
        cleaned = sanitize_input_text(v)
        return cleaned.lower()


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int = Field(..., description="Binary prediction output: 0 for low risk or legitimate, 1 for high risk")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of the high-risk class")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracing")
    processing_time_ms: float = Field(..., ge=0.0, description="Time taken to process the request and run prediction")


class BatchPredictionInput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    inputs: List[PredictionInput] = Field(..., min_length=1, max_length=100, description="List of prediction inputs to process in batch")


class BatchPredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    predictions: List[PredictionResponse] = Field(..., description="List of prediction responses")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracing")
    processing_time_ms: float = Field(..., ge=0.0, description="Total time taken to process the batch")


