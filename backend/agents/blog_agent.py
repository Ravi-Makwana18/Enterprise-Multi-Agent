import logging
from backend.services import llm_service

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert enterprise content reviewer and copy editor.
Analyze blog posts and articles for publication readiness.
Evaluate tone, clarity, grammar, and structural integrity.
Return ONLY valid JSON matching the specified schema."""

_PROMPT = """Evaluate the blog article below for corporate publication readiness.

Blog content:
{content}

Return ONLY a JSON object with these fields:
{{
  "score": <integer 0-100 reflecting editorial quality>,
  "approved": <true if score >= 75, else false>,
  "issues": [<list of specific flaws or weaknesses>],
  "recommendations": [<list of concrete improvement recommendations>],
  "message": "<concise editorial summary>",
  "status": "<approved|in review|rejected>",
  "risk_level": "<low|medium|high>",
  "requires_human_review": <true|false>
}}
"""


def analyze_blog(content: str) -> dict:
    prompt = _PROMPT.format(content=content[:3500])
    return llm_service.generate(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)
