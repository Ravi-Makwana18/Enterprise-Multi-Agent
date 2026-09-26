from backend.services import llm_service

_SYSTEM_PROMPT = """You are a professional blog writer and copy editor.
Rewrite content to improve grammar, readability, structure, and professional tone.
Return ONLY valid JSON matching the specified schema."""

_REWRITE_PROMPT = """Rewrite the blog content below to improve grammar, readability, structure, and professional tone.

Original blog:
{content}

Return ONLY a valid JSON object with exactly these fields:
{{
  "score": <integer 0-100 for the rewritten content quality>,
  "approved": <true if score >= 80>,
  "message": "<the full rewritten blog content>",
  "issues": [],
  "recommendations": [],
  "status": "in review",
  "risk_level": "low",
  "requires_human_review": false
}}"""


def ai_rewrite_blog(content: str) -> str:
    import json
    prompt = _REWRITE_PROMPT.format(content=content[:3000])
    result = llm_service.generate(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)
    return json.dumps(result)
