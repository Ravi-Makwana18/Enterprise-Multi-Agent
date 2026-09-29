from pydantic import BaseModel, Field, field_validator

from backend.config import settings


class UserRequest(BaseModel):
    model_config = {"extra": "ignore"}

    message: str = Field(..., min_length=1, max_length=settings.max_message_length)
    session_id: str | None = Field(default=None, description="Chat session ID for continuity.")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message cannot be empty")
        return trimmed


class ChatSessionUpdateRequest(BaseModel):
    model_config = {"extra": "ignore"}

    title: str = Field(..., min_length=1, max_length=255)



class LoginRequest(BaseModel):
    model_config = {"extra": "ignore"}

    employee_id: str | None = None
    username: str | None = None
    password: str = Field(default="")