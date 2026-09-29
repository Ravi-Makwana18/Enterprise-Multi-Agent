import logging

logger = logging.getLogger(__name__)


# NOTE: Active blog review is handled by agents/blog_ai_review.py::ai_review_blog().
# The prompt below documents the intended evaluation schema for reference.
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
