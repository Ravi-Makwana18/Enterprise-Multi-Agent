from backend.services import llm_service

_SYSTEM_PROMPT = """You are an expert enterprise editorial director and content reviewer.
Evaluate articles and blog posts rigorously against defined enterprise quality criteria:
1. Structure: Logical progression, section hierarchy, headings, introduction, and conclusion.
2. Clarity: Readability, clear expression, avoidance of ambiguous jargon.
3. Completeness: Comprehensiveness of ideas, depth, addressing core premises.
4. Consistency: Uniformity of tone, voice, terminology, and formatting.
5. Requested Standards: Alignment with corporate publishing guidelines, technical accuracy, and neutrality.

Return ONLY a valid JSON object matching the specified schema."""

_REVIEW_PROMPT = """Evaluate the article/blog content below against defined editorial quality criteria:

Blog content:
{content}

Return ONLY a valid JSON object with exactly these fields:
{{
  "score": <overall quality score 0-100>,
  "approved": <true if score >= 80, else false>,
  "quality_criteria": {{
    "structure": <score 0-100 evaluating organization and flow>,
    "clarity": <score 0-100 evaluating readability and expression>,
    "completeness": <score 0-100 evaluating depth and coverage>,
    "consistency": <score 0-100 evaluating tone and style uniformity>,
    "standards": <score 0-100 evaluating compliance with requested standards>
  }},
  "issues": [<list of specific flaws, gaps, or structural weaknesses>],
  "recommendations": [<list of concrete actionable improvements for the next revision cycle>],
  "message": "<2-4 sentence executive summary of review findings and recommendations>",
  "status": "<approved|in review|rejected>",
  "risk_level": "<low|medium|high>",
  "requires_human_review": <true if score is between 60 and 79 or if editorial verification is needed, else false>
}}"""


def ai_review_blog(content: str) -> dict:
    """Return the LLM review result as a dict evaluating defined quality criteria."""
    prompt = _REVIEW_PROMPT.format(content=content[:4000])
    res = llm_service.generate(prompt, model_key="blog", system_prompt=_SYSTEM_PROMPT)

    # Ensure quality_criteria dictionary exists even if model omitted it
    if "quality_criteria" not in res or not isinstance(res.get("quality_criteria"), dict):
        base_score = int(res.get("score") or 75)
        res["quality_criteria"] = {
            "structure": base_score,
            "clarity": base_score,
            "completeness": base_score,
            "consistency": base_score,
            "standards": base_score,
        }

    # Ensure requires_human_review flag aligns with criteria
    score = int(res.get("score") or 0)
    if "requires_human_review" not in res:
        res["requires_human_review"] = 60 <= score < 80

    return res

