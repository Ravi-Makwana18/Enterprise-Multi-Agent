from typing import Any, List, Optional
from backend.services import llm_service

_SYSTEM_PROMPT = """You are a senior enterprise blog writer and editorial copy editor.
Rewrite, enhance, and restructure content to address review findings and human feedback.
Improve structure, clarity, completeness, consistency, and alignment with requested standards.
Return ONLY a valid JSON object matching the specified schema."""

_REWRITE_PROMPT = """Revise and improve the article/blog content below based on previous review findings and editorial feedback.

Original content:
{content}

Identified issues to fix:
{issues}

Editorial recommendations to apply:
{recommendations}

Human reviewer feedback:
{human_feedback}

Return ONLY a valid JSON object with exactly these fields:
{{
  "score": <integer 0-100 reflecting rewritten content quality>,
  "approved": <true if score >= 80, else false>,
  "message": "<the full rewritten and polished article text>",
  "issues": [],
  "recommendations": [],
  "status": "<approved if score >= 80 else in review>",
  "risk_level": "low",
  "requires_human_review": false
}}"""


def ai_rewrite_blog(
    content: str,
    issues: Optional[List[str]] = None,
    recommendations: Optional[List[str]] = None,
    human_feedback: Optional[str] = None,
) -> dict[str, Any]:
    """Rewrite content targeting specific review findings and human feedback."""
    issues_text = "\n- ".join(issues) if issues else "None specified. Focus on structure, clarity, completeness, and consistency."
    if issues_text and not issues_text.startswith("\n- "):
        issues_text = f"- {issues_text}"

    recs_text = "\n- ".join(recommendations) if recommendations else "Elevate clarity, structure, and professional standards."
    if recs_text and not recs_text.startswith("\n- "):
        recs_text = f"- {recs_text}"

    hf_text = human_feedback.strip() if human_feedback else "None provided. Apply standard enterprise editorial criteria."

    prompt = _REWRITE_PROMPT.format(
        content=content[:3500],
        issues=issues_text,
        recommendations=recs_text,
        human_feedback=hf_text,
    )
    return llm_service.generate(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)

