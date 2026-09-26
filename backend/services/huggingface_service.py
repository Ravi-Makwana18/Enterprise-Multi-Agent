import json
import logging
import os
import re
from typing import Any

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# Free, high-performance instruction-following models on Hugging Face Serverless Router
HF_MODELS = {
    "default": "meta-llama/Llama-3.1-8B-Instruct",
    "blog": "meta-llama/Llama-3.1-8B-Instruct",
    "salary": "meta-llama/Llama-3.1-8B-Instruct",
    "security": "meta-llama/Llama-3.1-8B-Instruct",
    "support": "meta-llama/Llama-3.1-8B-Instruct",
    "router": "meta-llama/Llama-3.1-8B-Instruct",
}

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
_TIMEOUT = 45


def _get_token() -> str | None:
    return os.getenv("HUGGINGFACE_API_TOKEN") or getattr(settings, "huggingface_api_token", None)


def _call_hf_chat(
    prompt: str,
    model_key: str = "default",
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 768,
) -> str:
    token = _get_token()
    if not token:
        raise ValueError("HUGGINGFACE_API_TOKEN is not configured in .env.")

    model = HF_MODELS.get(model_key, HF_MODELS["default"])
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    else:
        messages.append({
            "role": "system",
            "content": "You are an enterprise AI assistant. Always return valid JSON only, without explanatory markdown or extra prose.",
        })

    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if choices and isinstance(choices, list):
        message = choices[0].get("message", {})
        return message.get("content", "").strip()

    raise ValueError(f"Unexpected response structure from Hugging Face: {data}")


def _extract_json(text: str) -> dict[str, Any]:
    """Robustly extract and normalize the first JSON object from model output."""
    clean = text.strip()

    # Remove markdown code blocks if present
    match_code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if match_code_block:
        candidate_str = match_code_block.group(1).strip()
    else:
        # Search for first outermost balanced { ... }
        match_brace = re.search(r"(\{[\s\S]*\})", clean)
        candidate_str = match_brace.group(1).strip() if match_brace else clean

    parsed = json.loads(candidate_str)
    if not isinstance(parsed, dict):
        raise ValueError(f"Extracted JSON is not an object: {type(parsed)}")

    # Normalize standard schema keys to prevent downstream type errors
    normalized: dict[str, Any] = dict(parsed)

    # Score
    if "score" in normalized:
        try:
            normalized["score"] = int(float(normalized["score"]))
            normalized["score"] = max(0, min(100, normalized["score"]))
        except (ValueError, TypeError):
            normalized["score"] = 75

    # Approved boolean
    if "approved" in normalized:
        raw_app = normalized["approved"]
        if isinstance(raw_app, str):
            normalized["approved"] = raw_app.strip().lower() in {"true", "yes", "1", "approved"}
        else:
            normalized["approved"] = bool(raw_app)

    # Lists
    for key in ("issues", "recommendations"):
        if key in normalized:
            val = normalized[key]
            if isinstance(val, list):
                normalized[key] = [str(x) for x in val]
            elif isinstance(val, str) and val.strip():
                normalized[key] = [val.strip()]
            else:
                normalized[key] = []
        else:
            normalized[key] = []

    # Requires human review
    if "requires_human_review" in normalized:
        val = normalized["requires_human_review"]
        if isinstance(val, str):
            normalized["requires_human_review"] = val.strip().lower() in {"true", "yes", "1"}
        else:
            normalized["requires_human_review"] = bool(val)

    return normalized


def generate_text(prompt: str, model_key: str = "default", system_prompt: str | None = None) -> str:
    """Generate freeform text from HuggingFace router."""
    try:
        return _call_hf_chat(
            prompt,
            model_key=model_key,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.warning("HuggingFace text generation failed (%s): %s", model_key, exc)
        return f"Unable to generate response via Hugging Face: {exc}"


def generate(prompt: str, model_key: str = "default", system_prompt: str | None = None) -> dict[str, Any]:
    """
    Call Hugging Face Serverless Chat API and return a parsed, normalized dictionary.
    Falls back gracefully on network or JSON parsing issues.
    """
    model_name = HF_MODELS.get(model_key, HF_MODELS["default"])
    try:
        raw_output = _call_hf_chat(
            prompt,
            model_key=model_key,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1024,
        )
        data = _extract_json(raw_output)
        data.setdefault("model", model_name)
        data.setdefault("fallback", False)
        return data
    except Exception as exc:
        logger.warning("HuggingFace call failed (%s): %s", model_key, exc)
        return {
            "score": 0,
            "approved": False,
            "issues": [str(exc)],
            "recommendations": ["Verify network access or check HuggingFace token and model availability."],
            "message": f"Hugging Face evaluation completed with fallback: {exc}",
            "status": "fallback",
            "risk_level": "high",
            "requires_human_review": True,
            "model": model_name,
            "fallback": True,
        }
