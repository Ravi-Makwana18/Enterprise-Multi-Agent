import logging
import re
from typing import Any

from backend.services import llm_service
from backend.services.ticket_service import create_ticket

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an Enterprise Service Desk & IT Operations Support Specialist.
Communicate directly, clearly, and helpfully with the employee seeking assistance.
Diagnose root causes, explain immediate resolution steps, and assign accurate taxonomy and priority.
Address the employee directly in a professional tone (e.g. "We have registered your ticket. Please follow these steps to reset your password:").
Do NOT speak in third-person meta-analysis (never say "The user requested..." or "The request is a standard...").
Do NOT use raw formatting asterisks like "**" or loose symbols in plain text.
Return ONLY valid JSON matching the specified schema."""

_PROMPT = """Triage and resolve the enterprise support request below.

Employee Support Request:
{request}
{knowledge_context}

Objectives:
- Urgency Score (0-100): 0-39 = low impact, 40-69 = normal, 70-89 = high, 90-100 = critical service outage/blocker.
- Category: accurately classify into 'it', 'security', 'payroll', 'hr', 'network', 'access', or 'general'.
- Priority: classify into 'low', 'normal', 'high', or 'urgent'.
- Message: provide a clear, direct, professional 2-3 sentence response addressed directly to the employee explaining what has been done and what they should do next.
- Issues: list 1 to 3 specific observed symptoms or technical blockers.
- Recommendations: list 2 to 4 clear, actionable step-by-step resolution or troubleshooting actions for the employee.
- Risk Level: 'low', 'medium', 'high', or 'critical'.

Return ONLY a valid JSON object:
{{
  "score": <integer 0-100 reflecting urgency>,
  "approved": true,
  "message": "<direct, helpful response addressed to the employee>",
  "issues": [<list of specific issue statements without asterisks>],
  "recommendations": [<list of clear actionable steps without asterisks>],
  "status": "submitted",
  "risk_level": "<low|medium|high|critical>",
  "requires_human_review": <true|false>,
  "suggested_category": "<it|security|payroll|hr|network|access|general>",
  "suggested_priority": "<low|normal|high|urgent>"
}}
"""


def create_support_ticket(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze support request with LLM triage reasoning and record a persistent ticket."""
    user_input = str(state.get("user_input", "")).strip()

    # 1. Detect greetings and capability inquiries (do not create tickets for greetings)
    clean_lower = re.sub(r"[^\w\s]", "", user_input.lower()).strip()
    greetings = {
        "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon",
        "good evening", "howdy", "who are you", "what can you do", "help",
        "what is this", "capabilities", "menu", "start"
    }
    if clean_lower in greetings or clean_lower.startswith(("hello", "hi there", "hey there", "what can you do")):
        state["response"] = {
            "status": "conversational",
            "message": (
                "Hello! I am your Enterprise Multi-Agent Assistant. I can assist you across four specialized domains:\n\n"
                "• 📝 **Blog Writer & Reviewer**: Compose or review articles with SEO and quality checks.\n"
                "• 💰 **Salary & Compensation**: Compute payroll, tax withholding, HRA, and compliance rules.\n"
                "• 🛡️ **Security & Compliance**: Audit employee credentials, Aadhaar/Passport, and police verification.\n"
                "• 🎫 **IT & Enterprise Support**: Triage technical incidents and log support tickets.\n\n"
                "How can I assist you today?"
            ),
            "issues": [],
            "recommendations": [
                "Calculate salary: 'Calculate salary for Alice: Basic ₹65,000, HRA ₹15,000, Bonus ₹5,000'",
                "Security check: 'Run security check for EMP-101, Passport: A1234567, Police: cleared'",
                "Write blog: 'Write a blog about microservices in enterprise banking'",
                "Support incident: 'Unable to connect to corporate VPN server from US-East region'"
            ],
            "score": 100.0,
            "approved": True,
            "risk_level": "low",
            "requires_human_review": False,
        }
        state["score"] = 100.0
        state["approved"] = True
        state["status"] = "conversational"
        return state

    # 2. Detect Ticket Inquiries & Lookups (do NOT create tickets when user is asking about tickets)
    if re.search(r"\b(my tickets|active tickets|show tickets|list tickets|any tickets|open tickets|check tickets|status of ticket|ticket status)\b", clean_lower) or clean_lower.startswith(("do i have any", "show my ticket", "what are my tickets")):
        from backend.services.ticket_service import list_tickets
        all_tickets = list_tickets()
        user_id = (state.get("user_employee_id") or state.get("employee_id") or state.get("user_name") or state.get("requester") or "").lower()
        if user_id and state.get("user_role") != "admin":
            user_tickets = [t for t in all_tickets if not t.get("requester") or user_id in (t.get("requester") or "").lower()]
        else:
            user_tickets = all_tickets

        if not user_tickets:
            msg = "You currently have no active or pending support tickets on file."
        else:
            msg = f"You have {len(user_tickets)} ticket(s) recorded in the system:\n\n" + "\n".join(
                f"• **{t['ticket_id']}** ({t.get('category', 'general').upper()}): {t.get('summary')} — Status: `{t.get('status', 'submitted').upper()}`"
                for t in user_tickets[:5]
            ) + "\n\nYou can track resolution progress or review notes in the **Tickets** tab."

        state["response"] = {
            "status": "ticket_lookup",
            "message": msg,
            "issues": [],
            "recommendations": ["Visit the Tickets tab to see full history or create a new support request."],
            "score": 100.0,
            "approved": True,
            "risk_level": "low",
            "requires_human_review": False,
        }
        state["score"] = 100.0
        state["approved"] = True
        state["status"] = "ticket_lookup"
        return state

    # Check for direct ticket ID query like "what is status of TKT-16b823a1"
    tkt_match = re.search(r"\b(TKT-[A-Za-z0-9]{8})\b", user_input, re.IGNORECASE)
    if tkt_match and any(w in clean_lower for w in ("status", "check", "view", "track", "what", "where", "find", "is", "about")):
        from backend.services.ticket_service import get_ticket
        tkt = get_ticket(tkt_match.group(1).upper())
        if tkt:
            audit_note = f"\n• **Reviewer Audit**: {tkt.get('review_notes')}" if tkt.get("review_notes") else ""
            reviewer_name = f"\n• **Reviewed By**: {tkt.get('reviewed_by')}" if tkt.get("reviewed_by") else ""
            state["response"] = {
                "status": "ticket_lookup",
                "message": (
                    f"Found Ticket Record **{tkt['ticket_id']}**:\n\n"
                    f"• **Summary**: {tkt.get('summary')}\n"
                    f"• **Status**: `{tkt.get('status', 'submitted').upper()}`\n"
                    f"• **Category**: {tkt.get('category', 'general').upper()}\n"
                    f"• **Priority**: {tkt.get('priority', 'normal').upper()}\n"
                    f"• **Requester**: {tkt.get('requester', 'N/A')}"
                    f"{reviewer_name}{audit_note}"
                ),
                "issues": [],
                "recommendations": ["You can track ticket progress in the Tickets tab."],
                "ticket_id": tkt["ticket_id"],
                "score": 100.0,
                "approved": True,
                "risk_level": "low",
                "requires_human_review": False,
            }
            state["score"] = 100.0
            state["approved"] = True
            state["status"] = "ticket_lookup"
            return state

    # 3. Check input sufficiency: too brief or vague to triage
    words = user_input.split()
    vague_terms = {"ticket", "issue", "bug", "broken", "problem", "error", "fail", "failed", "help me", "support"}
    if len(words) < 3 or clean_lower in vague_terms:
        state["response"] = {
            "status": "insufficient_input",
            "message": "The provided support request is too brief to diagnose the issue.",
            "issues": [
                "Missing specific application, system, or error description (fewer than 3 words provided)."
            ],
            "recommendations": [
                "Describe the affected application or service (e.g. VPN, Outlook, Database, SSO).",
                "Include what you were trying to do and any error codes or symptoms observed."
            ],
            "score": None,
            "approved": False,
            "risk_level": "low",
            "requires_human_review": False,
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "insufficient_input"
        return state

    # Extract requester email if present in text
    requester = state.get("requester")
    if not requester:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_input)
        requester = email_match.group(0) if email_match else "employee@enterprise.internal"

    # Retrieve relevant enterprise knowledge base / past solutions from vector store
    knowledge_context = ""
    try:
        from backend.services.vector_store_service import search_similar
        matches = search_similar(user_input, n_results=2)
        if matches:
            knowledge_context = "\nRelevant Enterprise Knowledge Base & Past Resolutions:\n" + "\n".join(
                f"- {m['content']}" for m in matches
            )
    except Exception as exc:
        logger.warning("Vector search error in support agent: %s", exc)

    prompt = _PROMPT.format(request=user_input[:2500], knowledge_context=knowledge_context)
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

    def _clean_text(val: Any) -> Any:
        if isinstance(val, str):
            # Remove raw ** and loose asterisks
            cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", val)
            return cleaned.replace("**", "").replace("*", "").replace("$", "₹")
        if isinstance(val, list):
            return [_clean_text(x) for x in val]
        return val

    clean_message = _clean_text(llm_result.get("message") or "We have received your support request and logged it into our system.")
    clean_issues = _clean_text(llm_result.get("issues", []))
    clean_recommendations = _clean_text(llm_result.get("recommendations", []))

    # Keep knowledge sources clean and brief (only genuinely relevant knowledge base articles)
    clean_knowledge = []
    for m in matches:
        content = m.get("content", "")
        if "Triage:" in content and "Ticket TKT-" in content:
            continue  # Skip old ticket artifacts
        clean_knowledge.append(_clean_text(content))

    state["response"] = {
        "message": clean_message,
        "issues": clean_issues,
        "recommendations": clean_recommendations,
        "ticket_id": ticket["ticket_id"],
        "summary": ticket["summary"],
        "category": ticket["category"],
        "priority": ticket["priority"],
        "requester": ticket["requester"],
        "created_at": ticket["created_at"],
        "status": ticket["status"],
        "risk_level": llm_result.get("risk_level", "low"),
        "requires_human_review": llm_result.get("requires_human_review", False),
        "knowledge_sources": clean_knowledge,
        "score": llm_result.get("score", 75),
        "approved": True,
    }
    state["score"] = float(llm_result.get("score", 75))
    state["approved"] = True
    state["status"] = ticket["status"]
    return state

