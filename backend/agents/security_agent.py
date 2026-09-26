import logging
import re
from typing import Any

from backend.services import llm_service
from backend.services.security_service import evaluate_security_check

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an Enterprise Information Security & Compliance Auditor.
Your responsibility is to assess personnel security records against corporate governance, ISO 27001, and SOC 2 standards.
Evaluate identity credentials, background checks, and police verifications.
Provide rigorous, risk-weighted assessments and concrete remediation guidance.
Return ONLY valid JSON matching the specified schema without conversational prose."""

_PROMPT = """Perform an enterprise personnel security evaluation based on the audit record below.

Audit Record:
- Employee Name: {name}
- Employee ID: {emp_id}
- Passport Status: {passport}
- Aadhaar / National ID: {aadhaar}
- Residential Address: {address}
- Police Background Verification: {police}
- Identified Missing Credentials: {missing}
- Policy & Format Issues: {rule_issues}
- Baseline Status: {rule_status}

Assessment Guidelines:
- If required credentials (passport, national ID, address) are missing or police check is pending, compliance score should reflect the risk (below 75).
- If background verification is incomplete, requires_human_review MUST be true.
- Outline specific remediation steps required for full security clearance.

Return ONLY a valid JSON object:
{{
  "score": <integer 0-100 reflecting compliance and trust posture>,
  "approved": <true if compliant and cleared, false otherwise>,
  "message": "<2-3 sentence executive security assessment>",
  "issues": [<list of specific security/compliance risks identified>],
  "recommendations": [<list of actionable remediation or verification steps>],
  "status": "<approved|in review|escalated|rejected>",
  "risk_level": "<low|medium|high|critical>",
  "requires_human_review": <true|false>
}}
"""


def _extract_security_record(state: dict[str, Any]) -> dict[str, Any]:
    """Extract security credentials and employee details from state or natural language input."""
    text = str(state.get("user_input", ""))

    # 1. Employee Name & ID
    emp_id = state.get("employee_id")
    if not emp_id:
        id_match = re.search(r"\b(EMP[-_]?[0-9]{3,6})\b", text, re.IGNORECASE)
        emp_id = id_match.group(1).upper() if id_match else "EMP001"

    emp_name = state.get("employee_name")
    if not emp_name:
        name_match = re.search(r"(?:for|employee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        emp_name = name_match.group(1).strip() if name_match else "Employee"

    # 2. Passport
    passport = state.get("passport")
    if not passport:
        p_match = re.search(r"passport\s*[:=]?\s*([A-Za-z0-9]{6,12})", text, re.IGNORECASE)
        passport = p_match.group(1) if p_match else ""

    # 3. Aadhaar / ID
    aadhaar = state.get("aadhaar")
    if not aadhaar:
        a_match = re.search(r"(?:aadhaar|national id|id)\s*[:=]?\s*([0-9]{12})", text, re.IGNORECASE)
        aadhaar = a_match.group(1) if a_match else ""

    # 4. Address
    address = state.get("address")
    if not address:
        addr_match = re.search(r"address\s*[:=]?\s*([^,\n;]+)", text, re.IGNORECASE)
        address = addr_match.group(1).strip() if addr_match else ""

    # 5. Police verification
    police = state.get("police_verification")
    if not police:
        if re.search(r"police\s*(?:check|verification)?\s*(?:cleared|verified|passed|done|ok)", text, re.IGNORECASE):
            police = "cleared"
        elif re.search(r"police\s*(?:check|verification)?\s*(?:pending|awaited|in progress)", text, re.IGNORECASE):
            police = "pending"
        else:
            police = "pending"

    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "passport": passport,
        "aadhaar": aadhaar,
        "address": address,
        "police_verification": police,
    }


def run_security_check(state: dict[str, Any]) -> dict[str, Any]:
    """Execute personnel security evaluation and perform deep LLM-driven compliance reasoning."""
    record = _extract_security_record(state)
    rule_result = evaluate_security_check(record)

    missing_str = ", ".join(rule_result.get("missing_fields", [])) or "None (all present)"
    issues_str = ", ".join(rule_result.get("issues", [])) or "None detected"

    prompt = _PROMPT.format(
        name=record["employee_name"],
        emp_id=record["employee_id"],
        passport=record["passport"] or "Not submitted",
        aadhaar=record["aadhaar"] or "Not submitted",
        address=record["address"] or "Not submitted",
        police=record["police_verification"],
        missing=missing_str,
        rule_issues=issues_str,
        rule_status=rule_result["status"],
    )

    llm_result = llm_service.generate(prompt, model_key="security", system_prompt=_SYSTEM_PROMPT)

    # Combine rule issues and LLM issues
    combined_issues = list(dict.fromkeys(rule_result.get("issues", []) + llm_result.get("issues", [])))
    final_status = rule_result["status"] if rule_result["status"] in {"escalated", "in review"} else llm_result.get("status", "approved")

    state["response"] = {
        **llm_result,
        "employee_id": rule_result["employee_id"],
        "employee_name": rule_result["employee_name"],
        "missing_fields": rule_result.get("missing_fields", []),
        "issues": combined_issues,
        "status": final_status,
        "approval_required": rule_result.get("approval_required", False) or llm_result.get("requires_human_review", False),
        "human_approval_required": rule_result.get("human_approval_required", False) or llm_result.get("requires_human_review", False),
    }
    state["score"] = llm_result.get("score", 70 if rule_result.get("approval_required") else 95)
    state["approved"] = llm_result.get("approved", not rule_result.get("approval_required", False))
    state["status"] = final_status
    return state
