from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Literal
from app.utils.validators import sanitize_input_text

class PredictionInput(BaseModel):
    age: int = Field(..., ge=18, le=120, description="Age of the entity/user", example=35)
    income: float = Field(..., ge=0.0, le=10000000.0, description="Annual income of the entity/user", example=75000.0)
    transaction_amount: float = Field(..., ge=0.0, le=5000000.0, description="Amount of the transaction to analyze", example=120.50)
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Pre-calculated risk score", example=0.23)
    department: Literal["finance", "healthcare", "other"] = Field(..., description="Department originating the request")
    user_role: Literal["admin", "analyst", "user"] = Field(..., description="Role of the user making the transaction")

    # Extra input validation via field validator (e.g. sanitization or specific business logic)
    @field_validator("department", "user_role")
    @classmethod
    def sanitize_string_fields(cls, v: str) -> str:
        # Strip HTML, log injection characters and normalize to lower case
        cleaned = sanitize_input_text(v)
        return cleaned.lower()

class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int = Field(..., description="Binary prediction output: 0 for low risk, 1 for high risk")
    probability: float = Field(..., description="Probability of high risk class")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracking")
    processing_time_ms: float = Field(..., description="Time taken to process request and run prediction")

class BatchPredictionInput(BaseModel):
    inputs: List[PredictionInput] = Field(..., min_items=1, max_items=100, description="List of prediction inputs to process in batch")

class BatchPredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    predictions: List[PredictionResponse] = Field(..., description="List of prediction responses")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracking")
    processing_time_ms: float = Field(..., description="Total time taken to process the batch")


