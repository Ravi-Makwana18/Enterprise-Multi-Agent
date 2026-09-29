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
{compliance_context}

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


def _extract_and_validate_security(
    state: dict[str, Any]
) -> tuple[dict[str, Any], bool, list[str], list[str], bool, str | None]:
    """Extract security credentials and employee details, validating input sufficiency."""
    text = str(state.get("user_input", "")).strip()

    # 1. Employee ID
    emp_id = state.get("employee_id")
    id_match = re.search(r"\b(EMP[-_]?[0-9]{3,6})\b", text, re.IGNORECASE)
    if not emp_id and id_match:
        emp_id = id_match.group(1).upper()

    db_emp = None
    db_sec = None
    if emp_id:
        try:
            from backend.services.employee_service import get_employee
            db_emp = get_employee(emp_id)
        except Exception:
            db_emp = None
        try:
            from backend.services.security_check_service import get_security_check_by_employee_id
            db_sec = get_security_check_by_employee_id(emp_id)
        except Exception:
            db_sec = None

    # 2. Employee Name
    emp_name = state.get("employee_name")
    if not emp_name:
        if db_emp:
            emp_name = db_emp.get("employee_name")
        elif db_sec:
            emp_name = db_sec.get("employee_name")
        else:
            name_match = re.search(r"(?:for|employee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
            emp_name = name_match.group(1).strip() if name_match else None

    # 3. Passport
    passport = state.get("passport")
    if not passport:
        p_match = re.search(r"passport\s*[:=]?\s*([A-Za-z0-9]{6,12})", text, re.IGNORECASE)
        passport = p_match.group(1) if p_match else (db_sec.get("passport") if db_sec and db_sec.get("passport") else "")

    # 4. Aadhaar / ID
    aadhaar = state.get("aadhaar")
    if not aadhaar:
        a_match = re.search(r"(?:aadhaar|national id|id)\s*[:=]?\s*([0-9]{12})", text, re.IGNORECASE)
        aadhaar = a_match.group(1) if a_match else (db_sec.get("aadhaar") if db_sec and db_sec.get("aadhaar") else "")

    # 5. Address
    address = state.get("address")
    if not address:
        addr_match = re.search(r"address\s*[:=]?\s*([^,\n;]+)", text, re.IGNORECASE)
        address = addr_match.group(1).strip() if addr_match else (db_sec.get("address") if db_sec and db_sec.get("address") else "")

    # 6. Police verification
    police = state.get("police_verification")
    has_police_mention = False
    if not police:
        if re.search(r"police\s*(?:check|verification)?\s*(?:cleared|verified|passed|done|ok)", text, re.IGNORECASE):
            police = "cleared"
            has_police_mention = True
        elif re.search(r"police\s*(?:check|verification)?\s*(?:pending|awaited|in progress)", text, re.IGNORECASE):
            police = "pending"
            has_police_mention = True
        elif db_sec and db_sec.get("police_verification"):
            police = db_sec["police_verification"]
            has_police_mention = True
        else:
            police = "pending"
    else:
        has_police_mention = True

    # ── Role-based Access Control Guard ──
    # If accessing an existing database employee's private credentials:
    # Admins have full access. Standard employees can ONLY inspect their own records.
    user_role = str(state.get("user_role") or "user").strip().lower()
    user_emp_id = state.get("user_employee_id")
    has_db_record = bool(db_sec or db_emp)
    target_id = emp_id or (db_emp["employee_id"] if db_emp else (db_sec["employee_id"] if db_sec else None))
    target_name = emp_name or (db_emp.get("employee_name") if db_emp else (db_sec.get("employee_name") if db_sec else "Employee"))

    if has_db_record and user_role != "admin":
        is_self = user_emp_id and target_id and user_emp_id.upper() == target_id.upper()
        if not is_self:
            denial_msg = (
                f"⛔ Access Denied: You do not have security clearance to access personnel verification "
                f"or identity credentials for employee {target_id} ({target_name}). "
                f"Access is strictly restricted to Corporate Security Administrators."
            )
            return {}, False, [
                f"Unauthorized personnel security check: Target '{target_id}', Requester Role: '{user_role}'"
            ], [
                "Security compliance audits for other employees can only be performed by Security Administrators.",
                "If you are checking your own clearance, provide your own Employee ID."
            ], False, denial_msg

    # Check input sufficiency:
    # Must have either an identified employee or at least one credential piece submitted
    has_credentials = bool(passport or aadhaar or address or has_police_mention)
    has_identity = bool(emp_id or emp_name)

    issues: list[str] = []
    recommendations: list[str] = []

    if not has_identity and not has_credentials:
        issues.append("Employee ID or Employee Name was not provided.")
        issues.append("No credential details provided (Passport, Aadhaar/National ID, Address, or Police clearance).")
    elif not has_identity:
        issues.append("Employee Name or ID is missing for credential association.")
    elif not has_credentials and not db_emp:
        issues.append("No credential documentation submitted for verification.")

    if issues:
        recommendations.append("Provide details: e.g., 'Run security check for EMP-101, Passport: A1234567, Aadhaar: 123456789012, Address: 123 Tech Park, Police: cleared'")
        recommendations.append("Or query an existing employee ID: e.g., 'Verify compliance for EMP-001'")
        return {}, False, issues, recommendations, True, None

    return {
        "employee_id": emp_id or (db_emp.get("employee_id") if db_emp else "EMP-GEN"),
        "employee_name": emp_name or "Employee",
        "passport": passport,
        "aadhaar": aadhaar,
        "address": address,
        "police_verification": police,
    }, True, [], [], True, None


def run_security_check(state: dict[str, Any]) -> dict[str, Any]:
    """Execute personnel security evaluation and perform deep LLM-driven compliance reasoning."""
    record, is_sufficient, issues, recommendations, is_authorized, auth_error = _extract_and_validate_security(state)

    if not is_authorized:
        logger.warning("Unauthorized security check access attempt: %s", issues)
        state["response"] = {
            "status": "forbidden",
            "message": auth_error or "⛔ Access Denied: Unauthorized access to employee security records.",
            "issues": issues,
            "recommendations": recommendations,
            "score": 0.0,
            "approved": False,
            "risk_level": "critical",
            "requires_human_review": True,
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "forbidden"
        return state

    if not is_sufficient:
        state["response"] = {
            "status": "insufficient_input",
            "message": "The provided input is insufficient to perform a security and compliance evaluation.",
            "issues": issues,
            "recommendations": recommendations,
            "score": None,
            "approved": False,
            "risk_level": "low",
            "requires_human_review": False,
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "insufficient_input"
        return state

    rule_result = evaluate_security_check(record)

    missing_str = ", ".join(rule_result.get("missing_fields", [])) or "None (all present)"
    issues_str = ", ".join(rule_result.get("issues", [])) or "None detected"

    # Query ChromaDB for compliance policies & background check standards
    compliance_context = ""
    knowledge_sources = []
    try:
        from backend.services.vector_store_service import search_similar
        matches = search_similar("ISO 27001 background check police verification identity standards", n_results=2)
        if matches:
            knowledge_sources = [m["content"] for m in matches]
            compliance_context = "\nApplicable Corporate Compliance Standards (from Knowledge Base):\n" + "\n".join(
                f"- {m['content']}" for m in matches
            )
    except Exception as exc:
        logger.warning("Vector search error in security agent: %s", exc)

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
        compliance_context=compliance_context,
    )

    llm_result = llm_service.generate(prompt, model_key="security", system_prompt=_SYSTEM_PROMPT)

    # Combine rule issues and LLM issues
    combined_issues = list(dict.fromkeys(rule_result.get("issues", []) + llm_result.get("issues", [])))
    final_status = rule_result["status"] if rule_result["status"] in {"escalated", "in review"} else llm_result.get("status", "approved")

    # Index audit record into vector store for audit trail and compliance recall
    try:
        from backend.services.vector_store_service import add_documents
        add_documents(
            documents=[f"Security Audit for {record['employee_name']} ({record['employee_id']}): Status {final_status}. Result: {llm_result.get('message', '')}"],
            metadatas=[{"category": "security_audit", "status": final_status, "employee_id": record["employee_id"]}],
            ids=[f"sec-audit-{record['employee_id']}"],
            collection_name="enterprise_knowledge",
        )
    except Exception:
        pass

    state["response"] = {
        **llm_result,
        "employee_id": rule_result["employee_id"],
        "employee_name": rule_result["employee_name"],
        "missing_fields": rule_result.get("missing_fields", []),
        "issues": combined_issues,
        "status": final_status,
        "knowledge_sources": knowledge_sources,
        "approval_required": rule_result.get("approval_required", False) or llm_result.get("requires_human_review", False),
        "human_approval_required": rule_result.get("human_approval_required", False) or llm_result.get("requires_human_review", False),
    }
    state["score"] = llm_result.get("score", 70 if rule_result.get("approval_required") else 95)
    state["approved"] = llm_result.get("approved", not rule_result.get("approval_required", False))
    state["status"] = final_status
    return state
