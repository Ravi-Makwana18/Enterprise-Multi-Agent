import logging
import re
from typing import Any

from backend.services import llm_service
from backend.services.ticket_service import create_ticket

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an Enterprise Service Desk & IT Operations Triage Specialist.
Analyze incoming enterprise support incidents, service requests, and technical issues.
Diagnose root causes, gauge business impact, assign precision taxonomy and priority,
and provide immediate first-line troubleshooting recommendations.
Return ONLY valid JSON matching the specified schema without conversational prose."""

_PROMPT = """Triage the enterprise support request below.

Incoming Support Request:
{request}

Triage Objectives:
- Urgency Score (0-100): 0-39 = low impact, 40-69 = normal, 70-89 = high, 90-100 = critical service outage/blocker.
- Category: accurately classify into 'it', 'security', 'payroll', 'hr', 'network', 'access', or 'general'.
- Priority: classify into 'low', 'normal', 'high', or 'urgent'.
- Issues: isolate 1 to 4 core failure symptoms or bottlenecks.
- Recommendations: provide 2 to 4 immediate, actionable technical remediation or workaround steps.
- Message: provide a clear, professional 2-3 sentence incident diagnosis and next action plan.
- Requires Human Review: true if priority is high/urgent or security-related, else false.

Return ONLY a valid JSON object:
{{
  "score": <integer 0-100 reflecting incident urgency>,
  "approved": true,
  "message": "<2-3 sentence diagnostic summary and immediate advice>",
  "issues": [<list of specific problem statements>],
  "recommendations": [<list of actionable resolution or troubleshooting steps>],
  "status": "submitted",
  "risk_level": "<low|medium|high|critical>",
  "requires_human_review": <true|false>,
  "suggested_category": "<it|security|payroll|hr|network|access|general>",
  "suggested_priority": "<low|normal|high|urgent>"
}}
"""


def create_support_ticket(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze support request with LLM triage reasoning and record a persistent ticket."""
    user_input = str(state.get("user_input", "")).strip() or "General inquiry regarding enterprise systems."

    # Extract requester email if present in text
    requester = state.get("requester")
    if not requester:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_input)
        requester = email_match.group(0) if email_match else "employee@enterprise.internal"

    prompt = _PROMPT.format(request=user_input[:2500])
    llm_result = llm_service.generate(prompt, model_key="support", system_prompt=_SYSTEM_PROMPT)

    category = str(llm_result.get("suggested_category", state.get("category", "general"))).lower()
    if category not in {"it", "security", "payroll", "hr", "network", "access", "general"}:
        category = "general"

    priority = str(llm_result.get("suggested_priority", state.get("priority", "normal"))).lower()
    if priority not in {"low", "normal", "high", "urgent"}:
        priority = "normal"

    # Generate a concise summary title for ticket tracking
    summary = user_input.split("\n")[0][:120] if user_input else "Support Request"

    ticket = create_ticket(
        summary=summary,
        category=category,
        priority=priority,
        requester=requester,
        assignee=state.get("assignee"),
    )

    state["response"] = {
        **llm_result,
        "ticket_id": ticket["ticket_id"],
        "summary": ticket["summary"],
        "category": ticket["category"],
        "priority": ticket["priority"],
        "requester": ticket["requester"],
        "created_at": ticket["created_at"],
        "status": ticket["status"],
    }
    state["score"] = llm_result.get("score", 50)
    state["approved"] = llm_result.get("approved", True)
    state["status"] = ticket["status"]
    return state
