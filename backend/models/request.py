from pydantic import BaseModel, Field, field_validator

from backend.config import settings


class UserRequest(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(..., min_length=1, max_length=settings.max_message_length)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message cannot be empty")
        return trimmed