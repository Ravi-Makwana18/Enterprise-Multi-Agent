import json
import logging
import os
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", getattr(settings, "llm_provider", "groq")).strip().lower()


def _has_aws_credentials() -> bool:
    key = os.getenv("AWS_ACCESS_KEY_ID") or getattr(settings, "aws_access_key_id", None)
    return bool(key and key.strip() and not key.startswith("your_"))


def generate(prompt: str, model_key: str = "default", system_prompt: str | None = None) -> dict[str, Any]:
    provider = _get_provider()

    if provider == "bedrock":
        return _bedrock(prompt, model_key)

    if provider == "auto" and _has_aws_credentials():
        result = _bedrock(prompt, model_key)
        if not result.get("fallback"):
            return result
        logger.info("Bedrock fallback; routing to Groq for model_key=%s", model_key)

    if provider == "huggingface":
        return _hf(prompt, model_key, system_prompt)

    # Default: Groq (free, fast)
    return _groq(prompt, model_key, system_prompt)


def generate_text(prompt: str, model_key: str = "default", system_prompt: str | None = None) -> str:
    provider = _get_provider()
    if provider == "bedrock" and _has_aws_credentials():
        data = _bedrock(prompt, model_key)
        return data.get("message", str(data))
    if provider == "huggingface":
        from backend.services.huggingface_service import generate_text as hf_text
        return hf_text(prompt, model_key, system_prompt)
    # Default: Groq — fall back gracefully if key is not configured
    try:
        from backend.services.groq_service import generate_text as groq_text
        return groq_text(prompt, model_key, system_prompt)
    except Exception:
        from backend.services.groq_service import _local_fallback
        return _local_fallback(model_key, prompt).get("message", "Request processed.")



def _bedrock(prompt: str, model_key: str) -> dict[str, Any]:
    try:
        from backend.services.bedrock_service import BedrockService
        svc = BedrockService()
        raw = svc.generate(prompt, model_key=model_key)
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed
    except Exception as exc:
        logger.warning("Bedrock unavailable (%s): %s", model_key, exc)
        return {"fallback": True, "issues": [str(exc)], "score": 0, "approved": False,
                "status": "fallback", "risk_level": "high", "requires_human_review": True}


def _hf(prompt: str, model_key: str, system_prompt: str | None = None) -> dict[str, Any]:
    from backend.services.huggingface_service import generate as hf_generate
    return hf_generate(prompt, model_key, system_prompt)


def _groq(prompt: str, model_key: str, system_prompt: str | None = None) -> dict[str, Any]:
    from backend.services.groq_service import generate as groq_generate
    return groq_generate(prompt, model_key, system_prompt)
