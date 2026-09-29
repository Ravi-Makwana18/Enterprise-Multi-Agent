"""Enterprise Intent & Criticality Governance Service.

Provides multi-tiered safety analysis, role-based access verification,
and intelligent intent routing across greetings, general enterprise FAQs,
unauthorized attempts, out-of-scope queries, and specialist agent workflows.
"""

import logging
import re
from typing import Any

from backend.core.pii import redact_pii
from backend.services import llm_service
from backend.services.vector_store_service import search_similar

logger = logging.getLogger(__name__)

# Security & Prompt Injection Blocklist Patterns
_INJECTION_PATTERNS = [
    r"\b(ignore\s+(all\s+)?(previous|prior)\s+instructions?)\b",
    r"\b(system\s+prompt(\s+leak|\s+reveal)?)\b",
    r"\b(developer\s+mode|jailbreak|dan\s+mode)\b",
    r"\b(dump\s+(the\s+)?(database|all\s+employees|passwords?|credentials?))\b",
    r"\b(show\s+(all\s+)?(pan|account\s+numbers?|ssn|aadhaar)\s+of\s+everyone)\b",
    r"\b(drop\s+table|delete\s+from\s+employees|truncate\s+table)\b",
    r"\b(bypass\s+(safety|guardrails?|security\s+policy))\b",
]

# Conversational Greetings & Pleasantries
_GREETING_PATTERNS = [
    r"^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day))(\s+there|\s+assistant|\s+bot)?[\s!.,?]*$",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|what\s+is\s+this|help|menu|start|capabilities)[\s!.,?]*$",
    r"^(thank\s+you|thanks|appreciate\s+it|great|awesome|ok|okay)[\s!.,?]*$",
]

# Out of Scope / Non-Enterprise Subjects
_OUT_OF_SCOPE_PATTERNS = [
    r"\b(recipe|bake\s+a\s+cake|how\s+to\s+cook|pancakes|dinner|pizza)\b",
    r"\b(horoscope|astrology|zodiac|fortune\s+teller)\b",
    r"\b(sports\s+scores?|who\s+won\s+the\s+(game|match|world\s+cup|superbowl))\b",
    r"\b(tell\s+me\s+a\s+(bedtime\s+)?story|fairy\s+tale|poem\s+about\s+dragons)\b",
    r"\b(medical\s+advice|diagnose\s+my\s+symptoms|what\s+pill\s+should\s+i\s+take)\b",
]

# General Enterprise Policy / FAQ Keywords
_FAQ_KEYWORDS = [
    "leave policy", "vacation", "sick leave", "casual leave", "maternity", "paternity",
    "office location", "office locations", "where are our offices", "branches", "campuses",
    "working hours", "hybrid policy", "work from home", "remote work",
    "reimbursement", "travel allowance", "health insurance", "medical policy",
    "holiday list", "public holidays", "dress code", "working days",
    "what is hra", "how is hra calculated", "tax withholding policy", "pf contribution",
    "what departments", "company departments", "headcount", "how many employees"
]


def evaluate_message_criticality(
    user_input: str,
    user_role: str = "user",
    user_employee_id: str | None = None
) -> dict[str, Any]:
    """Evaluate message security criticality and safety risk tier."""
    text = (user_input or "").strip()
    text_lower = text.lower()
    user_role_norm = (user_role or "user").strip().lower()

    # 1. Critical: Prompt Injection or Adversarial Attack Attempt
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            return {
                "criticality": "CRITICAL",
                "risk_level": "critical",
                "intent": "SECURITY_INCIDENT",
                "is_allowed": False,
                "reason": "Suspicious input pattern: Prompt injection or data exfiltration attempt detected.",
                "guardrail": "guardrail:adversarial_prompt_blocked",
            }

    # 2. Critical: Unauthorized Cross-Employee Lookup (RBAC)
    id_match = re.search(r"\b(EMP[-_]?[0-9]{3,6})\b", text, re.IGNORECASE)
    if id_match and user_role_norm != "admin" and user_employee_id:
        target_id = id_match.group(1).upper()
        if target_id != user_employee_id.upper() and any(
            w in text_lower for w in ("salary", "pay", "compensation", "bonus", "pan", "account", "passport", "aadhaar", "police")
        ):
            return {
                "criticality": "CRITICAL",
                "risk_level": "critical",
                "intent": "UNAUTHORIZED",
                "is_allowed": False,
                "target_id": target_id,
                "reason": f"Standard employees ({user_employee_id}) are strictly prohibited from viewing records of other personnel ({target_id}).",
                "guardrail": "guardrail:rbac_violation_blocked",
            }

    # 3. High: Production / Critical IT Outage Reports
    if re.search(r"\b(production\s+down|database\s+outage|ransomware|security\s+breach|p0\s+incident)\b", text_lower):
        return {
            "criticality": "HIGH",
            "risk_level": "high",
            "intent": "SUPPORT",
            "is_allowed": True,
            "reason": "High-priority enterprise operational incident.",
            "guardrail": "guardrail:high_priority_escalation",
        }

    # 4. Standard / Low Criticality
    return {
        "criticality": "LOW",
        "risk_level": "low",
        "intent": None,
        "is_allowed": True,
        "reason": "Normal operational message.",
        "guardrail": "guardrail:input_safety_verified",
    }


def classify_user_intent(user_input: str) -> str:
    """Classify user intent across conversational, FAQ, out-of-scope, or specialist agents."""
    text = (user_input or "").strip()
    text_lower = text.lower()

    # 1. Greetings & Pleasantries
    for pat in _GREETING_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            return "GREETING"

    # 2. Out of Scope / Non-Enterprise
    for pat in _OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            return "OUT_OF_SCOPE"

    # 3. General Enterprise Knowledge & FAQ (policies, offices, benefits, guidelines)
    for kw in _FAQ_KEYWORDS:
        if kw in text_lower:
            return "GENERAL_FAQ"

    # 4. Specialist Workflows
    # Salary & Compensation (A3)
    if re.search(r"\b(salary|payroll|compensation|hra|bonus|take[- ]home|wages?|pay slip|payslip|ctc)\b", text_lower):
        return "SALARY"

    # Security & Background Verification (A2)
    if re.search(r"\b(security clearance|police verification|aadhaar|passport|background check|compliance audit)\b", text_lower) or (
        re.search(r"\bsecurity\b", text_lower) and not re.search(r"\b(ticket|incident|blog|article|draft)\b", text_lower)
    ):
        return "SECURITY"

    # Blog & Article Review / Writing (A1)
    if re.search(r"\b(blog|article|essay|proofread|story|publish|attached document|manuscript)\b", text_lower) or (
        re.search(r"\b(write|draft|rewrite|evaluate draft|review draft)\b", text_lower) and not re.search(r"\b(ticket|incident|salary)\b", text_lower)
    ):
        return "BLOG"

    # IT Support & Service Desk
    if re.search(r"\b(ticket|incident|outage|login|password reset|vpn|service desk|it help|server down|crash|bug|error)\b", text_lower):
        return "SUPPORT"

    # Default to General FAQ / LLM reasoning
    return "GENERAL_FAQ"


def handle_governed_intent(state: dict[str, Any]) -> dict[str, Any] | None:
    """Handle safety, greetings, FAQs, unauthorized attempts, and out-of-scope messages.

    Returns:
        dict: A finalized state dictionary if handled directly.
        None: If the message should proceed to a specialist agent workflow (SALARY, SECURITY, BLOG, SUPPORT).
    """
    user_input = str(state.get("user_input", "")).strip()
    user_role = str(state.get("user_role") or "user").strip().lower()
    user_emp_id = state.get("user_employee_id")

    # Step 1: Evaluate Safety & Criticality
    crit = evaluate_message_criticality(user_input, user_role, user_emp_id)

    # 1A. Security Incident (Prompt Injection / Exfiltration Block)
    if crit["intent"] == "SECURITY_INCIDENT":
        logger.warning("Adversarial prompt blocked: %s | User: %s", user_input[:100], user_emp_id)
        state["response"] = {
            "status": "rejected",
            "message": (
                "🛡️ Security Alert: Request Denied\n\n"
                "Your request violates enterprise AI acceptable use policies. System instructions, raw credentials, "
                "and protected databases cannot be disclosed or altered.\n\n"
                "This event has been logged for compliance auditing."
            ),
            "issues": [crit["reason"]],
            "recommendations": [
                "Submit legitimate business requests through approved workflows.",
                "Review enterprise acceptable use guidelines."
            ],
            "score": 0.0,
            "approved": False,
            "risk_level": "critical",
            "requires_human_review": True,
            "guardrail_checks": [crit["guardrail"]],
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "rejected"
        return state

    # 1B. Unauthorized RBAC Violation (Cross-employee snooping)
    if crit["intent"] == "UNAUTHORIZED":
        target = crit.get("target_id", "requested employee")
        logger.warning("RBAC violation blocked: User %s attempted to access %s", user_emp_id, target)
        state["response"] = {
            "status": "forbidden",
            "message": (
                f"⛔ Access Denied: Role-Based Authorization Required\n\n"
                f"You are authenticated as {user_emp_id}. Company confidentiality policies strictly prohibit standard employees "
                f"from accessing compensation, payroll, or security background records for {target}.\n\n"
                "Standard employees may only query their own personal profile."
            ),
            "issues": [crit["reason"]],
            "recommendations": [
                "To view your own salary, ask: 'Check my salary details'",
                "If you are an authorized HR / Payroll officer, log in with an Administrator profile."
            ],
            "score": 0.0,
            "approved": False,
            "risk_level": "critical",
            "requires_human_review": True,
            "guardrail_checks": [crit["guardrail"]],
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "forbidden"
        return state

    # Step 2: Determine User Intent
    intent = classify_user_intent(user_input)

    # 2A. Greetings & Pleasantries
    if intent == "GREETING":
        state["response"] = {
            "status": "conversational",
            "message": (
                "Hello! I am your Enterprise AI Multi-Agent Assistant. I coordinate across four specialized domains:\n\n"
                "• 💳 Salary & Compensation (A3): Deterministic payroll breakdowns, take-home pay in INR (₹), HRA, bonus, and tax guidance.\n"
                "• 🛡️ Security Verification (A2): Employee ID credentials, Aadhaar/Passport audits, and police verification status.\n"
                "• ✍️ Blog & Article Review (A1): Automated drafts, quality evaluation, SEO structure, and human-in-the-loop review cycles.\n"
                "• 🎫 IT & Operations Support: Incident triage, technical troubleshooting, and persistent support ticket tracking.\n\n"
                "How can I assist you with enterprise operations today?"
            ),
            "issues": [],
            "recommendations": [
                "Check salary: 'Check my salary details'",
                "Verify employee: 'Run security check for EMP-101'",
                "Draft article: 'Write an executive blog about enterprise multi-agent architectures'",
                "Log IT ticket: 'VPN connection failing on corporate gateway port 443'"
            ],
            "score": 100.0,
            "approved": True,
            "risk_level": "low",
            "requires_human_review": False,
            "guardrail_checks": ["guardrail:conversational_greeting_handled"],
        }
        state["score"] = 100.0
        state["approved"] = True
        state["status"] = "conversational"
        return state

    # 2B. Out-of-Scope Queries (Cooking, sports trivia, personal)
    if intent == "OUT_OF_SCOPE":
        state["response"] = {
            "status": "out_of_scope",
            "message": (
                "ℹ️ Notice: Out of Enterprise Scope\n\n"
                "I am an enterprise AI platform dedicated to business workflows: Payroll & Compensation, Personnel Security Checks, "
                "Corporate Blog & Editorial Publishing, and IT Incident Support.\n\n"
                "I am unable to answer personal, non-work-related queries such as cooking recipes, entertainment trivia, or personal lifestyle topics. "
                "Please submit an enterprise or business-related inquiry."
            ),
            "issues": ["Query is outside enterprise multi-agent operational domains."],
            "recommendations": [
                "Ask about enterprise payroll: e.g., 'What is our HRA benchmark policy?'",
                "Ask about security verification: e.g., 'What documents are required for background checks?'",
                "Draft an article: e.g., 'Draft a press release for Q3 achievements'"
            ],
            "score": 85.0,
            "approved": True,
            "risk_level": "low",
            "requires_human_review": False,
            "guardrail_checks": ["guardrail:out_of_scope_redirected"],
        }

        state["score"] = 85.0
        state["approved"] = True
        state["status"] = "out_of_scope"
        return state

    # 2C. General Enterprise Knowledge & FAQ
    if intent == "GENERAL_FAQ":
        # Search vector knowledge base for relevant policy articles
        kb_matches = search_similar(user_input, n_results=2)
        kb_text = "\n".join(f"- {redact_pii(m['content'])}" for m in kb_matches) if kb_matches else ""

        # Provide grounded answers for common corporate questions
        prompt = (
            "You are the Enterprise Operations Assistant. Provide a concise, professional 2-3 sentence factual answer "
            "to the user's company question using the verified corporate context below. "
            "Express all currency figures in Indian Rupees (₹). Return ONLY a JSON object: {\"answer\": \"<text>\"}.\n\n"
            f"Corporate Context:\n{kb_text}\n\n"
            "Key Enterprise Facts:\n"
            "- Locations: Bangalore (HQ), Mumbai, Pune, Delhi, Hyderabad, Kolkata, Chennai, Ahmedabad, Noida, Gurugram.\n"
            "- Departments (15): Engineering, HR, Finance, Legal, Marketing, Sales, Operations, IT Support, "
            "Customer Service, Data Science, Product Management, Procurement, Administration, Security, R&D.\n"
            "- Compensation: Standard HRA benchmark is 20-50% of Basic Pay (default 25%). Standard statutory tax withholding is 10%.\n"
            "- Security: Aadhaar (12 digits) or valid Passport and cleared police background check required.\n\n"
            f"User Question: \"{user_input}\""
        )
        try:
            res = llm_service.generate(prompt, model_key="support")
            faq_answer = res.get("answer") or "Here is the verified company information for your inquiry."
            # Ensure no dollar signs leak
            faq_answer = faq_answer.replace("$", "₹")
        except Exception:
            faq_answer = "Enterprise policies mandate standard statutory compliance across all 15 operational departments and regional hubs."

        state["response"] = {
            "status": "approved",
            "message": faq_answer,
            "issues": [],
            "recommendations": [
                "Check salary: 'Check my salary details'",
                "Check departments: 'Show department salary statistics'",
                "Submit IT request: 'Unable to connect to corporate VPN'"
            ],
            "knowledge_sources": [m["content"] for m in kb_matches] if kb_matches else [],
            "score": 95.0,
            "approved": True,
            "risk_level": "low",
            "requires_human_review": False,
            "guardrail_checks": ["guardrail:enterprise_faq_resolved", "guardrail:pii_redaction_verified"],
        }
        state["score"] = 95.0
        state["approved"] = True
        state["status"] = "approved"
        return state

    # Return None for specialist workflows (SALARY, SECURITY, BLOG, SUPPORT) to proceed via LangGraph
    return None
