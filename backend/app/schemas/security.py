from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class AuditLogSchema(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the event")
    user: str = Field(..., description="Username associated with the action")
    endpoint: str = Field(..., description="Request path")
    status: int = Field(..., description="HTTP status code returned")
    ip_address: str = Field(..., description="Client IP address")
    latency_ms: float = Field(..., description="Processing latency in milliseconds")
    prediction: Optional[Any] = Field(None, description="Prediction output if prediction endpoint")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional context or metadata")

class SecurityEventSchema(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the event")
    event: str = Field(..., description="Type of security event")
    user: str = Field(..., description="Username or identifier")
    status: str = Field(..., description="Status of the event, e.g. FAILED, SUCCESS")
    ip_address: str = Field(..., description="Client IP address")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional context or metadata")
