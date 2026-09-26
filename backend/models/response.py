from typing import Any

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    route: str = Field(..., description="The route chosen for this user request.")
    response: Any = Field(default_factory=dict, description="Structured response payload from the selected workflow.")
    score: int | None = Field(default=None, description="Quality score when available.")
    approved: bool | None = Field(default=None, description="Approval flag when available.")
    iteration: int = Field(default=0, description="Workflow iteration count.")


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    app: str
    environment: str
    version: str = "1.0.0"
    uptime_seconds: float
    checks: dict[str, bool]


class DiagnosticResponse(BaseModel):
    status: str
    environment: str
    app: str
    checks: dict[str, bool]
    config: dict[str, Any]


class ErrorResponse(BaseModel):
    error: dict[str, Any]
