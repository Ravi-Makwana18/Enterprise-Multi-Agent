import json
import os
import re

import boto3
from botocore.config import Config
from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.config import settings
from backend.core.secrets import get_secret


MODEL_REGISTRY = {
    "default": {
        "model_id": os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id),
        "version": "2026.09.25",
        "max_tokens": 512,
        "temperature": 0.0,
        "cost_per_1k_tokens": 0.008,
    },
    "blog_review": {
        "model_id": os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id),
        "version": "blog-review-v1",
        "max_tokens": 512,
        "temperature": 0.2,
        "cost_per_1k_tokens": 0.008,
    },
    "salary_review": {
        "model_id": os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id),
        "version": "salary-review-v1",
        "max_tokens": 512,
        "temperature": 0.1,
        "cost_per_1k_tokens": 0.008,
    },
    "security_review": {
        "model_id": os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id),
        "version": "security-review-v1",
        "max_tokens": 512,
        "temperature": 0.1,
        "cost_per_1k_tokens": 0.008,
    },
    "support_triage": {
        "model_id": os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id),
        "version": "support-triage-v1",
        "max_tokens": 512,
        "temperature": 0.1,
        "cost_per_1k_tokens": 0.008,
    },
}

PROMPT_REGISTRY = {
    "default": {"version": "v1", "instructions": "Return ONLY valid JSON with explicit score, approved, issues, recommendations, status, risk_level, requires_human_review."},
    "blog_review": {"version": "blog-review-v1", "instructions": "Review the blog for quality and return strict JSON. Never output prose outside JSON."},
    "salary_review": {"version": "salary-review-v1", "instructions": "Evaluate payroll risk, policy compliance, and approvals. Return strict JSON."},
    "security_review": {"version": "security-review-v1", "instructions": "Evaluate security controls and return decision JSON, including human-review triggers."},
    "support_triage": {"version": "support-triage-v1", "instructions": "Classify support cases and route to workflow states with mandatory JSON output."},
}


class StructuredDecisionOutput(BaseModel):
    score: int = Field(..., ge=0, le=100)
    approved: bool
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    status: str = Field(default="submitted")
    risk_level: str = Field(default="low")
    requires_human_review: bool = False
    model: str | None = None
    prompt_version: str | None = None
    usage: dict = Field(default_factory=dict)
    guardrail_checks: list[str] = Field(default_factory=list)
    fallback: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        allowed = {"submitted", "in review", "approved", "rejected", "escalated", "fallback"}
        if value not in allowed:
            raise ValueError(f"Invalid status: {value}")
        return value

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value):
        allowed = {"low", "medium", "high", "critical"}
        if value not in allowed:
            raise ValueError(f"Invalid risk_level: {value}")
        return value


class BedrockService:
    def __init__(self):
        self.local_mode = os.getenv("LOCAL_MODE", str(settings.local_mode)).lower() == "true"
        self.region = os.getenv("AWS_REGION", settings.aws_region)
        self.model_id = os.getenv("BEDROCK_MODEL_ID", settings.bedrock_model_id)
        self.model_registry = MODEL_REGISTRY.copy()
        self.prompt_registry = PROMPT_REGISTRY.copy()
        self.model_key = os.getenv("BEDROCK_MODEL_KEY", "default")
        self.timeout_seconds = int(os.getenv("BEDROCK_TIMEOUT_SECONDS", "30"))
        self.max_retries = int(os.getenv("BEDROCK_MAX_RETRIES", "3"))
        self.client = None
        self.usage_log = []

        if not self.local_mode:
            aws_key = get_secret(
                settings.secret_name,
                "AWS_ACCESS_KEY_ID",
                os.getenv("AWS_ACCESS_KEY_ID", settings.aws_access_key_id),
            )
            aws_secret = get_secret(
                settings.secret_name,
                "AWS_SECRET_ACCESS_KEY",
                os.getenv("AWS_SECRET_ACCESS_KEY", settings.aws_secret_access_key),
            )
            # Use setup_default_session to avoid overriding Lambda-reserved env vars
            if aws_key and aws_secret:
                boto3.setup_default_session(
                    aws_access_key_id=aws_key,
                    aws_secret_access_key=aws_secret,
                    region_name=self.region,
                )

            aws_config = Config(
                connect_timeout=self.timeout_seconds,
                read_timeout=self.timeout_seconds,
                retries={"max_attempts": self.max_retries + 1, "mode": "adaptive"},
            )
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=aws_config,
            )

    def get_model_config(self, model_key: str | None = None) -> dict:
        return self.model_registry.get(model_key or self.model_key, self.model_registry["default"])

    def _fallback_response(self, prompt: str, reason: str = "Model call failed") -> dict:
        result = {
            "score": 0,
            "approved": False,
            "issues": ["LLM output validation failed", reason],
            "recommendations": ["Human review required before using this decision"],
            "status": "fallback",
            "risk_level": "high",
            "requires_human_review": True,
            "model": self.model_id,
            "prompt_version": self.prompt_registry.get(self.model_key, {}).get("version", "v1"),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0},
            "guardrail_checks": ["fallback_path_used"],
            "fallback": True,
        }
        self.usage_log.append({"prompt_length": len(prompt), "status": "fallback", "reason": reason})
        return result

    def _estimate_usage(self, prompt: str, text: str, model_config: dict) -> dict:
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = max(1, len(str(text).split()))
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = (total_tokens / 1000.0) * float(model_config.get("cost_per_1k_tokens", 0.008))
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        }
        self.usage_log.append({"usage": usage, "model": model_config.get("model_id", self.model_id)})
        return usage

    def _policy_checks(self, candidate: dict, prompt: str) -> list[str]:
        checks = []
        policy_keywords = ["ignore previous instructions", "system prompt", "api key", "password", "secret", "bypass"]
        payload_text = json.dumps(candidate).lower() + " " + prompt.lower()

        for keyword in policy_keywords:
            if keyword in payload_text:
                checks.append(f"guardrail:{keyword.replace(' ', '_')}")

        if candidate.get("score") is not None and not 0 <= int(candidate["score"]) <= 100:
            checks.append("guardrail:score_out_of_range")

        if candidate.get("approved") is True and candidate.get("score", 0) < 50:
            checks.append("guardrail:high_risk_approval")

        return checks

    def _normalize_response(self, raw_payload: dict, prompt: str, model_key: str | None, model_config: dict) -> dict:
        candidate = raw_payload or {}
        candidate.setdefault("score", 0)
        candidate.setdefault("approved", False)
        candidate.setdefault("issues", [])
        candidate.setdefault("recommendations", [])

        try:
            structured = StructuredDecisionOutput(
                score=int(candidate.get("score", 0)),
                approved=bool(candidate.get("approved", False)),
                issues=[str(item) for item in candidate.get("issues", [])],
                recommendations=[str(item) for item in candidate.get("recommendations", [])],
                status=str(candidate.get("status", "approved" if candidate.get("approved") else "rejected")).lower(),
                risk_level=str(candidate.get("risk_level", "low")).lower(),
                requires_human_review=bool(candidate.get("requires_human_review", False)),
                model=model_config.get("model_id", self.model_id),
                prompt_version=self.prompt_registry.get(model_key or self.model_key, {}).get("version", "v1"),
                usage={},
                guardrail_checks=[],
                fallback=False,
            )
        except ValidationError:
            raise ValueError("LLM output failed schema validation")

        if structured.score <= 40 or structured.status in {"escalated", "in review"}:
            structured.requires_human_review = True
            structured.risk_level = "high"
        elif structured.score <= 70:
            structured.risk_level = "medium"
        else:
            structured.risk_level = "low"

        if structured.approved and structured.risk_level in {"medium", "high"}:
            structured.requires_human_review = True

        guardrail_issues = self._policy_checks(candidate, prompt)
        if guardrail_issues:
            structured.guardrail_checks = guardrail_issues
            structured.requires_human_review = True
            structured.risk_level = "high"
            structured.issues = list(dict.fromkeys(structured.issues + guardrail_issues))

        structured.usage = self._estimate_usage(prompt, json.dumps(candidate), model_config)
        return structured.model_dump()

    def _extract_text_from_response(self, response: dict) -> str:
        response_body = response.get("body")
        if response_body is None:
            raise ValueError("No Bedrock response body")

        if hasattr(response_body, "read"):
            body = response_body.read()
        else:
            body = response_body

        if isinstance(body, bytes):
            body = body.decode("utf-8")

        data = json.loads(body)
        text = ""
        if "content" in data:
            text = "".join(item.get("text", "") for item in data.get("content", []) if isinstance(item, dict))
        elif "completion" in data:
            text = str(data.get("completion", ""))
        elif "output" in data and isinstance(data["output"], dict):
            text = str(data["output"].get("text", ""))
        else:
            text = json.dumps(data)

        return text

    def _parse_model_payload(self, payload: str) -> dict:
        text = payload.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Model output is not a JSON object")
        return parsed

    def generate(self, prompt: str, model_key: str | None = None, prompt_version: str | None = None):
        model_key = model_key or self.model_key
        model_config = self.get_model_config(model_key)
        resolved_prompt_version = prompt_version or self.prompt_registry.get(model_key, {}).get("version", "v1")

        if self.local_mode:
            local_payload = {
                "score": 65,
                "approved": False,
                "issues": ["Missing conclusion", "Content too short"],
                "recommendations": ["Add conclusion", "Expand examples"],
                "status": "in review",
                "risk_level": "medium",
                "requires_human_review": True,
                "model": model_config.get("model_id", self.model_id),
                "prompt_version": resolved_prompt_version,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0},
                "guardrail_checks": [],
                "fallback": True,
            }
            return json.dumps(local_payload)

        if self.client is None:
            return json.dumps(self._fallback_response(prompt, "Bedrock client is not configured"))

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": model_config.get("max_tokens", 512),
            "temperature": model_config.get("temperature", 0.0),
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=model_config.get("model_id", self.model_id),
                    body=json.dumps(payload),
                    contentType="application/json",
                    accept="application/json",
                )
                text = self._extract_text_from_response(response)
                parsed = self._parse_model_payload(text)
                return json.dumps(self._normalize_response(parsed, prompt, model_key, model_config))
            except Exception as exc:
                if attempt == self.max_retries:
                    return json.dumps(self._fallback_response(prompt, str(exc)))

        return json.dumps(self._fallback_response(prompt, "Unknown Bedrock failure"))