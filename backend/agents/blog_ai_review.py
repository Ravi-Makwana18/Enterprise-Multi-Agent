from backend.services import llm_service

_SYSTEM_PROMPT = """You are an expert blog editor. Review blog content for publication readiness.
Evaluate clarity, structure, grammar, completeness, and professional tone.
Return ONLY valid JSON matching the specified schema."""

_REVIEW_PROMPT = """Review the blog content below and return ONLY a valid JSON object.

Blog content:
{content}

Return a JSON object with exactly these fields:
{{
  "score": <integer 0-100>,
  "approved": <true if score >= 80, else false>,
  "issues": [<list of specific issues found>],
  "recommendations": [<list of concrete improvements>],
  "message": "<2-3 sentence summary of the review>",
  "status": "<approved|in review|rejected>",
  "risk_level": "<low|medium|high>",
  "requires_human_review": <true|false>
}}"""


def ai_review_blog(content: str) -> str:
    import json
    prompt = _REVIEW_PROMPT.format(content=content[:3000])
    result = llm_service.generate(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)
    return json.dumps(result)
