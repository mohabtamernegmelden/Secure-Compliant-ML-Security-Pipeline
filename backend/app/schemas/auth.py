from pydantic import BaseModel, Field, field_validator
import re
from app.utils.validators import sanitize_input_text

class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for login", example="analyst")
    password: str = Field(..., min_length=8, max_length=128, description="Password for login", example="AnalystPass123!")

    @field_validator("username")
    @classmethod
    def validate_username_alphanumeric(cls, v: str) -> str:
        # Sanitize input first
        cleaned = sanitize_input_text(v)
        # Prevent SQL Injection and shell injection by strictly validating alphanumeric characters
        if not re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
            raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return cleaned.lower()

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Token type, typically bearer")
    role: str = Field(..., description="Role associated with the authenticated user")

class RefreshTokenInput(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT Refresh Token")

class UserProfile(BaseModel):
    username: str
    role: str
    is_active: bool
