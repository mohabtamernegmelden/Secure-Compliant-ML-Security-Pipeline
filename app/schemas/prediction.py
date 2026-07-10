from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import sanitize_input_text


class PredictionInput(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "step": 1,
                "type": "TRANSFER",
                "amount": 2500.0,
                "oldbalanceOrg": 5000.0,
                "newbalanceOrig": 2500.0,
                "oldbalanceDest": 1000.0,
                "newbalanceDest": 3500.0,
            }
        },
    )

    step: int | None = Field(default=None, ge=0, le=10000, description="Simulation step or transaction sequence index")
    type: str | None = Field(default=None, description="Transaction type")
    amount: float | None = Field(default=None, ge=0.0, le=100000000.0, description="Transaction amount")
    oldbalanceOrg: float | None = Field(default=None, ge=0.0, description="Original balance of the origin account")
    newbalanceOrig: float | None = Field(default=None, ge=0.0, description="New balance of the origin account")
    oldbalanceDest: float | None = Field(default=None, ge=0.0, description="Original balance of the destination account")
    newbalanceDest: float | None = Field(default=None, ge=0.0, description="New balance of the destination account")

    @field_validator("type", mode="before")
    @classmethod
    def sanitize_string_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = sanitize_input_text(str(value))
        return cleaned.upper() if cleaned else None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int | str = Field(..., description="Prediction label or class index")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of the predicted class")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracing")
    processing_time_ms: float = Field(..., ge=0.0, description="Time taken to process the request and run prediction")


class BatchPredictionInput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    inputs: list[PredictionInput] = Field(..., min_length=1, max_length=100, description="List of prediction inputs to process in batch")


class BatchPredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    predictions: list[PredictionResponse] = Field(..., description="List of prediction responses")
    model_version: str = Field(..., description="Version of the model that served this prediction")
    request_id: str = Field(..., description="Correlation ID for auditing and tracing")
    processing_time_ms: float = Field(..., ge=0.0, description="Total time taken to process the batch")


