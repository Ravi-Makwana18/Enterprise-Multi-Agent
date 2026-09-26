import logging
import re
from typing import Any

from backend.services import llm_service
from backend.services.pii_service import mask_account_number, mask_pan
from backend.services.salary_service import calculate_salary

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an enterprise Compensation & Payroll Compliance Specialist.
Your duty is to review computed employee compensation packages, assess tax withholdings and allowance ratios,
identify potential discrepancies or policy violations, and provide audit-grade recommendations.
Return ONLY valid JSON matching the specified schema without conversational prose."""

_PROMPT = """Analyze the computed compensation breakdown below and provide an executive payroll assessment.

Payroll Record:
- Employee Name: {name}
- Employee ID: {emp_id}
- Basic Salary: ${basic:,.2f}
- House Rent Allowance (HRA): ${hra:,.2f}
- Bonus / Incentives: ${bonus:,.2f}
- Calculated Gross Salary: ${gross:,.2f}
- Estimated Tax Withholding (10% standard): ${tax:,.2f}
- Net Take-Home Salary: ${net:,.2f}
- Policy Status: {status}
- Escalation Required: {approval}

Review Guidelines:
- Evaluate the HRA to Basic ratio (standard benchmark: 20-50% of basic).
- Assess if the bonus proportion is anomalous.
- Score payroll health from 0 to 100.
- Approved should be true unless high risk / regulatory concerns are detected.
- If gross exceeds escalation threshold or components are unusual, flag for human review.

Return ONLY a JSON object:
{{
  "score": <integer 0-100 reflecting payroll health and policy compliance>,
  "approved": <true|false>,
  "message": "<2-3 sentence executive payroll summary>",
  "issues": [<list of specific payroll or tax concerns, or empty list if none>],
  "recommendations": [<list of concrete payroll suggestions or next steps>],
  "status": "<approved|in review|escalated|rejected>",
  "risk_level": "<low|medium|high>",
  "requires_human_review": <true|false>
}}
"""


def _extract_salary_params(state: dict[str, Any]) -> dict[str, Any]:
    """Extract salary parameters from explicit state fields or natural language user_input."""
    text = str(state.get("user_input", ""))

    # 1. Employee Name & ID
    emp_id = state.get("employee_id")
    if not emp_id:
        id_match = re.search(r"\b(EMP[-_]?[0-9]{3,6})\b", text, re.IGNORECASE)
        emp_id = id_match.group(1).upper() if id_match else "EMP-001"

    emp_name = state.get("employee_name")
    if not emp_name:
        name_match = re.search(r"(?:for|employee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        emp_name = name_match.group(1).strip() if name_match else "Employee"

    # 2. Extract Basic Salary
    basic = state.get("basic_salary")
    if basic is None:
        b_match = re.search(r"(?:basic|base)(?:\s+salary)?\s*[:=]?\s*\$?([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        basic = float(b_match.group(1)) if b_match else 50000.0
    else:
        basic = float(basic)

    # 3. Extract HRA
    hra = state.get("hra")
    if hra is None:
        h_match = re.search(r"\bhra\s*[:=]?\s*\$?([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        hra = float(h_match.group(1)) if h_match else 10000.0
    else:
        hra = float(hra)

    # 4. Extract Bonus
    bonus = state.get("bonus")
    if bonus is None:
        bon_match = re.search(r"\b(?:bonus|incentive)\s*[:=]?\s*\$?([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        bonus = float(bon_match.group(1)) if bon_match else 5000.0
    else:
        bonus = float(bonus)

    # Bound inputs within validation limits
    basic = max(0.0, min(500000.0, basic))
    hra = max(0.0, min(150000.0, hra))
    bonus = max(0.0, min(100000.0, bonus))

    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "basic_salary": basic,
        "hra": hra,
        "bonus": bonus,
        "pan": state.get("pan", "ABCDE1234F"),
        "account_number": state.get("account_number", "1234567890123456"),
    }


def calculate_employee_salary(state: dict[str, Any]) -> dict[str, Any]:
    """Execute payroll computation and perform deep LLM-driven compliance reasoning."""
    params = _extract_salary_params(state)

    salary_result = calculate_salary(
        basic_salary=params["basic_salary"],
        hra=params["hra"],
        bonus=params["bonus"],
    )

    prompt = _PROMPT.format(
        name=params["employee_name"],
        emp_id=params["employee_id"],
        basic=salary_result["basic_salary"],
        hra=salary_result["hra"],
        bonus=salary_result["bonus"],
        gross=salary_result["gross_salary"],
        tax=salary_result["tax"],
        net=salary_result["net_salary"],
        status=salary_result["status"],
        approval=salary_result["approval_required"],
    )

    llm_result = llm_service.generate(prompt, model_key="salary", system_prompt=_SYSTEM_PROMPT)

    # Merge computation results with LLM analysis
    state["response"] = {
        **llm_result,
        "employee_id": params["employee_id"],
        "employee_name": params["employee_name"],
        "basic_salary": salary_result["basic_salary"],
        "hra": salary_result["hra"],
        "bonus": salary_result["bonus"],
        "gross_salary": salary_result["gross_salary"],
        "tax": salary_result["tax"],
        "net_salary": salary_result["net_salary"],
        "pan": mask_pan(params["pan"]),
        "account_number": mask_account_number(params["account_number"]),
        "approval_required": salary_result["approval_required"],
    }
    state["score"] = llm_result.get("score", 85)
    state["approved"] = llm_result.get("approved", not salary_result["approval_required"])
    state["status"] = salary_result["status"]
    return state
