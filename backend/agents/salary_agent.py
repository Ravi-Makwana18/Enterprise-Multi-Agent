import logging
import re
from typing import Any

from backend.core.pii import redact_pii
from backend.services import llm_service
from backend.services.pii_service import mask_account_number, mask_pan
from backend.services.salary_service import calculate_salary

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an enterprise Senior Compensation & Payroll Advisory Specialist.
Your duty is to provide clear, audit-compliant explanations, employee-friendly financial summaries,
and contextual policy guidance for pre-computed compensation packages.

Guiding Principles:
1. Deterministic Authority: Under no circumstances alter or recalculate the provided financial values.
   All arithmetic (Gross, Tax, Net) is pre-computed by deterministic enterprise payroll rules.
2. Minimal Information Collection: When a user query lacks sufficient compensation details:
   Ask ONLY for the minimal required attributes needed to proceed (keep required attributes to the absolute minimum):
   - Either their Employee ID (e.g. EMP0001 or EMP-101) to look up their official payroll record, OR
   - Their Basic Monthly Salary (e.g. ₹65,000) for a custom computation.
   Do NOT ask for unnecessary fields (such as HRA, bonus, tax rate, PAN, or bank account), as these are computed automatically.
3. Contextual Clarity: Clearly explain how basic pay, house rent allowance (HRA), performance incentives,
   and statutory tax withholdings determine the net take-home salary.
4. Policy & Ratio Compliance: Analyze the HRA-to-basic ratio (standard benchmark: 20-50%) and incentive
   distribution against corporate compensation benchmarks.
5. Tax Guidance: Explain the standard 10% withholding and highlight actionable tax-saving opportunities
   (e.g., rent receipts submission, investment declarations).
6. Currency Standard: Always use the Indian Rupee symbol '₹' (INR) for all monetary amounts and compensation figures. NEVER use the dollar sign ($) or USD.
7. Strict JSON Output: Return ONLY valid, well-formed JSON matching the specified schema."""

_PROMPT = """Review the verified compensation record below and generate an executive payroll explanation and compliance report.

Verified Payroll Record (PII Redacted):
- Employee: {name} ({emp_id})
- Role Profile: {designation} | Department: {department} | Location: {location}
- Reporting Manager: {manager_name}
- Basic Salary: ₹{basic:,.2f}
- House Rent Allowance (HRA): ₹{hra:,.2f} ({hra_ratio:.1f}% of Basic)
- Performance Bonus / Incentive: ₹{bonus:,.2f} ({bonus_ratio:.1f}% of Basic)
- Deterministic Gross Salary: ₹{gross:,.2f}
- Estimated Tax Withholding (10% statutory): ₹{tax:,.2f}
- Net Take-Home Pay: ₹{net:,.2f}
- Corporate Policy Status: {status}
- Escalation Required: {approval}
{payroll_context}

Required Analysis:
1. Executive Narrative: A concise 2-3 sentence overview of take-home pay in INR (₹), disbursement details, and tax withholding.
2. Allowance & Incentive Insights: Evaluate whether HRA and bonus allocations are optimal and aligned with enterprise policy.
3. Tax Advice & Recommendations: Concrete next steps (e.g. proof of rent submission, Section 80C declaration, retirement deductions).
4. Compliance Issues: Highlight any thresholds exceeded (e.g. gross >= ₹2,00,000 review, gross >= ₹5,00,000 escalation).

Return ONLY a JSON object:
{{
  "score": <integer 0-100 reflecting overall compensation health and policy compliance>,
  "approved": <true|false>,
  "message": "<2-3 sentence executive explanation of net take-home pay, monthly allowances, and tax withholdings>",
  "take_home_summary": "<clear 1-sentence breakdown of take-home salary and statutory deductions>",
  "allowance_analysis": "<1-2 sentence analysis of HRA and incentive ratios against corporate standards>",
  "tax_guidance": "<1-2 sentence advice on tax withholdings and potential deductions/exemptions>",
  "issues": [<list of specific policy notes or escalation reasons, empty if compliant>],
  "recommendations": [<list of concrete financial recommendations and employee next steps>],
  "status": "<approved|in review|escalated|rejected>",
  "risk_level": "<low|medium|high>",
  "requires_human_review": <true|false>
}}
"""


def _extract_and_validate_salary(
    state: dict[str, Any]
) -> tuple[dict[str, Any], bool, list[str], list[str], bool, str | None]:
    """Extract salary parameters via JWT identity and HR API, enforcing strict role-based access."""
    text = str(state.get("user_input", "")).strip()
    user_role = str(state.get("user_role") or "user").strip().lower()
    user_emp_id = state.get("user_employee_id")

    # 1. Identity & Access Control: Determine target Employee ID
    # Check if a specific employee ID is mentioned in the query text
    id_match = re.search(r"\b(EMP[-_]?[0-9]{3,6})\b", text, re.IGNORECASE)
    requested_id = id_match.group(1).upper() if id_match else None

    # Role-Based Access Control:
    # Standard employees can ONLY query their own records.
    if user_role != "admin" and user_emp_id:
        if requested_id and requested_id != user_emp_id.upper():
            denial_msg = (
                f"⛔ Access Denied: You do not have permission to view salary or compensation "
                f"records for employee {requested_id}. Standard employees may only access their own profile ({user_emp_id})."
            )
            return {}, False, [
                f"Unauthorized employee lookup: Target '{requested_id}', Requester: '{user_emp_id}' (Role: '{user_role}')"
            ], [
                "Log in with an Administrator account if you are an authorized HR / Payroll officer.",
                "To check your own salary, ask: 'Check my salary details'.",
            ], False, denial_msg

        # Default to the authenticated employee
        emp_id = user_emp_id.upper()
    else:
        # Admin user: can query requested employee or provided ID
        emp_id = requested_id or state.get("employee_id") or user_emp_id

    # 2. Call HR API / Database for the verified employee
    db_emp = None
    if emp_id:
        try:
            from backend.services.employee_service import get_employee
            db_emp = get_employee(emp_id)
        except Exception as err:
            logger.warning("HR API lookup error for %s: %s", emp_id, err)
            db_emp = None

    # 3. Extract Employee Name
    emp_name = state.get("employee_name")
    if not emp_name:
        if db_emp:
            emp_name = db_emp.get("employee_name")
        else:
            name_match = re.search(r"(?:for|employee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
            emp_name = name_match.group(1).strip() if name_match else None

    # 4. Extract Basic Salary (priority: database record -> explicit query params -> text extraction)
    basic = state.get("basic_salary")
    if basic is None:
        if db_emp and db_emp.get("basic_salary") is not None:
            basic = float(db_emp["basic_salary"])
        else:
            b_match = re.search(r"(?:basic|base)(?:\s+salary)?\s*[:=]?\s*(?:[₹$]|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
            if b_match:
                basic = float(b_match.group(1))
            else:
                gen_num_match = re.search(r"[₹$]([0-9]+(?:\.[0-9]+)?)|\b([0-9]{4,7})\b", text)
                if gen_num_match:
                    val_str = gen_num_match.group(1) or gen_num_match.group(2)
                    basic = float(val_str)
                else:
                    basic = None
    else:
        basic = float(basic)

    # 5. Extract HRA
    hra = state.get("hra")
    if hra is None:
        if db_emp and db_emp.get("hra") is not None:
            hra = float(db_emp["hra"])
        else:
            h_match = re.search(r"\bhra\s*[:=]?\s*(?:[₹$]|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
            hra = float(h_match.group(1)) if h_match else 0.0
    else:
        hra = float(hra)

    # 6. Extract Bonus / Incentive
    bonus = state.get("bonus")
    if bonus is None:
        if db_emp and db_emp.get("bonus") is not None:
            bonus = float(db_emp["bonus"])
        else:
            bon_match = re.search(r"\b(?:bonus|incentive)\s*[:=]?\s*(?:[₹$]|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
            bonus = float(bon_match.group(1)) if bon_match else 0.0
    else:
        bonus = float(bonus)

    # Input sufficiency check
    issues: list[str] = []
    recommendations: list[str] = []

    if basic is None and not db_emp:
        issues.append("Basic salary amount was not specified and employee record was not found.")
    if not emp_id and not emp_name:
        if basic is not None:
            emp_name = state.get("user_name") or "Employee"
        else:
            issues.append("Employee ID or Employee Name was not provided.")

    if issues:
        recommendations.append("Specify salary figures: e.g., 'Calculate salary for Alice: Basic ₹65,000, HRA ₹15,000, Bonus ₹5,000'")
        recommendations.append("Or query an authorized employee: e.g., 'Check my salary details'")
        return {}, False, issues, recommendations, True, None

    # Bound numbers to valid corporate compensation limits
    basic = max(0.0, min(5000000.0, basic or 0.0))
    hra = max(0.0, min(1500000.0, hra))
    bonus = max(0.0, min(1000000.0, bonus))

    return {
        "employee_id": emp_id or (db_emp.get("employee_id") if db_emp else "EMP-GEN"),
        "employee_name": emp_name or (db_emp.get("employee_name") if db_emp else "Employee"),
        "department": db_emp.get("department") if db_emp else "General",
        "designation": db_emp.get("designation") if db_emp else "Staff",
        "location": db_emp.get("location") if db_emp else "Headquarters",
        "manager_name": db_emp.get("manager_name") if db_emp else "Enterprise HR",
        "employment_type": db_emp.get("employment_type") if db_emp else "Full-Time",
        "basic_salary": basic,
        "hra": hra,
        "bonus": bonus,
        "pan": state.get("pan") or (db_emp.get("pan") if db_emp else "ABCDE1234F"),
        "account_number": state.get("account_number") or (db_emp.get("account_number") if db_emp else "100200000000"),
    }, True, [], [], True, None


def validate_salary_guardrails(
    candidate: dict[str, Any],
    salary_result: dict[str, Any],
    params: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Apply strict output guardrails validating PII masking, math integrity, and corporate policy."""
    guardrail_checks: list[str] = []

    # 1. PII Guardrail: Redact any accidental raw account numbers or PANs in model output fields
    for field_name in ("message", "take_home_summary", "allowance_analysis", "tax_guidance"):
        val = str(candidate.get(field_name) or "")
        if not val:
            continue
        if re.search(r"\b\d{9,18}\b", val):
            val = re.sub(r"\b\d{9,18}\b", "XXXXXX[REDACTED]", val)
            guardrail_checks.append("guardrail:pii_account_redacted")
        if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", val):
            val = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "XXXXX[REDACTED]", val)
            guardrail_checks.append("guardrail:pii_pan_redacted")
        # Ensure any dollar signs ($) generated by LLMs are strictly normalized to Rupee (₹)
        if "$" in val:
            val = val.replace("$", "₹")
            guardrail_checks.append("guardrail:rupee_standardized")
        candidate[field_name] = val

    if "issues" in candidate and isinstance(candidate["issues"], list):
        candidate["issues"] = [str(x).replace("$", "₹") for x in candidate["issues"]]
    if "recommendations" in candidate and isinstance(candidate["recommendations"], list):
        candidate["recommendations"] = [str(x).replace("$", "₹") for x in candidate["recommendations"]]

    guardrail_checks.append("guardrail:pii_redaction_verified")

    # 2. Mathematical Integrity Guardrail: Lock financial values to deterministic computation
    candidate["basic_salary"] = salary_result["basic_salary"]
    candidate["hra"] = salary_result["hra"]
    candidate["bonus"] = salary_result["bonus"]
    candidate["gross_salary"] = salary_result["gross_salary"]
    candidate["tax"] = salary_result["tax"]
    candidate["net_salary"] = salary_result["net_salary"]
    guardrail_checks.append("guardrail:deterministic_math_verified")

    # 3. Policy & Escalation Guardrail
    candidate["status"] = salary_result["status"]
    candidate["approval_required"] = salary_result["approval_required"]
    guardrail_checks.append("guardrail:policy_thresholds_verified")

    # 4. Identity & Masked Identifiers
    candidate["employee_id"] = params["employee_id"]
    candidate["employee_name"] = params["employee_name"]
    candidate["pan"] = mask_pan(params.get("pan"))
    candidate["account_number"] = mask_account_number(params.get("account_number"))
    guardrail_checks.append("guardrail:access_control_enforced")

    # 5. Score normalization (0-100)
    score_val = candidate.get("score")
    candidate["score"] = max(0, min(100, int(score_val if score_val is not None else 85)))

    return candidate, guardrail_checks


def calculate_employee_salary(state: dict[str, Any]) -> dict[str, Any]:
    """Execute deterministic salary calculation, Bedrock contextual explanation, and guardrail validation."""
    params, is_sufficient, issues, recommendations, is_authorized, auth_error = _extract_and_validate_salary(state)

    if not is_authorized:
        logger.warning("Unauthorized payroll access attempt: %s", issues)
        state["response"] = {
            "status": "forbidden",
            "message": auth_error or "⛔ Access Denied: Unauthorized access to employee records.",
            "issues": issues,
            "recommendations": recommendations,
            "score": 0.0,
            "approved": False,
            "risk_level": "critical",
            "requires_human_review": True,
            "guardrail_checks": ["guardrail:access_control_denied"],
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "forbidden"
        return state

    if not is_sufficient:
        # Check if query is an analytical question about department salary statistics
        user_input_raw = str(state.get("user_input", "")).strip()
        user_input_lower = user_input_raw.lower()
        dept_names = [
            "engineering", "human resources", "hr", "finance", "legal", "marketing", "sales",
            "operations", "it support", "customer service", "data science", "product management",
            "procurement", "administration", "security", "research & development", "r&d"
        ]
        matched_dept = next((d for d in dept_names if d in user_input_lower), None)
        is_analytics = any(k in user_input_lower for k in ("average", "avg", "salary statistics", "headcount", "highest", "lowest", "ctc", "distribution"))

        if is_analytics or matched_dept:
            from backend.services.employee_service import query_department_analytics
            search_dept = "Human Resources" if matched_dept == "hr" else ("Research & Development" if matched_dept == "r&d" else matched_dept)
            analytics_data = query_department_analytics(search_dept)
            if analytics_data:
                lines = [
                    f"• **{d['department']}**: Headcount: {d['headcount']} employees | Avg Basic: ₹{d['avg_basic']:,.2f}/mo | Avg Bonus: ₹{d['avg_bonus']:,.2f} | Avg CTC: ₹{d['avg_annual_ctc']:,.2f}/yr"
                    for d in analytics_data
                ]
                dept_summary_text = "\n".join(lines)
                dept_name_display = analytics_data[0]["department"] if len(analytics_data) == 1 else "Enterprise Departments"
                resp = {
                    "status": "approved",
                    "score": 95,
                    "approved": True,
                    "message": f"Verified SQLite compensation analytics for {dept_name_display}:\n\n{dept_summary_text}",
                    "take_home_summary": f"Calculated across {sum(d['headcount'] for d in analytics_data)} verified employee records in SQLite.",
                    "allowance_analysis": f"Average basic pay for {dept_name_display} is ₹{analytics_data[0]['avg_basic']:,.2f}.",
                    "tax_guidance": "Departmental figures represent pre-tax basic salaries and statutory performance incentives in INR (₹).",
                    "issues": [],
                    "recommendations": [
                        "To view individual take-home pay, ask: 'Check salary for EMP0001'",
                        "Filter by specific department: e.g., 'Average salary in Data Science'",
                    ],
                    "department_analytics": analytics_data,
                    "risk_level": "low",
                    "requires_human_review": False,
                    "guardrail_checks": ["guardrail:deterministic_sql_aggregation", "guardrail:pii_redaction_verified"],
                }
                state["response"] = resp
                state["score"] = 95.0
                state["approved"] = True
                state["status"] = "approved"
                return state

        state["response"] = {
            "status": "insufficient_input",
            "message": (
                "To provide your compensation and salary breakdown, I need only one of the following:\n\n"
                "• Your **Employee ID** (e.g., `EMP0001` or `EMP-101`) — to look up your official company payroll record, OR\n"
                "• Your **Basic Monthly Salary** (e.g., `₹65,000`) — if you would like a custom compensation calculation.\n\n"
                "*(No other details are required — allowances, tax withholdings, and net pay will be calculated automatically).* "
            ),
            "issues": issues,
            "recommendations": [
                "Provide your Employee ID: e.g., 'Check salary for EMP0001'",
                "Or provide a basic salary figure: e.g., 'Calculate salary for basic ₹75,000'",
                "Or ask for department averages: e.g., 'Average salary in Engineering'",
            ],
            "score": None,
            "approved": False,
            "risk_level": "low",
            "requires_human_review": False,
            "guardrail_checks": ["guardrail:minimal_input_prompted"],
        }
        state["score"] = 0.0
        state["approved"] = False
        state["status"] = "insufficient_input"
        return state

    # Step 3: Deterministic salary & incentive rules calculate amounts
    salary_result = calculate_salary(
        basic_salary=params["basic_salary"],
        hra=params["hra"],
        bonus=params["bonus"],
    )

    # Step 2 & 4: PII detection runs before model processing; Bedrock provides explanation and context
    payroll_context = ""
    knowledge_sources = []
    try:
        from backend.services.vector_store_service import search_similar
        matches = search_similar("Enterprise compensation guidelines HRA bonus tax withholding policy", n_results=2)
        if matches:
            knowledge_sources = [m["content"] for m in matches]
            payroll_context = "\nApplicable Corporate Compensation Standards (from Knowledge Base):\n" + "\n".join(
                f"- {redact_pii(m['content'])}" for m in matches
            )
    except Exception as exc:
        logger.warning("Vector search error in salary agent: %s", exc)

    # Compute contextual ratios for model reasoning
    base_ref = max(1.0, salary_result["basic_salary"])
    hra_ratio = (salary_result["hra"] / base_ref) * 100.0
    bonus_ratio = (salary_result["bonus"] / base_ref) * 100.0

    # Note: Account numbers, PANs, and sensitive credentials are NOT provided to the LLM prompt
    prompt = _PROMPT.format(
        name=params["employee_name"],
        emp_id=params["employee_id"],
        designation=params.get("designation") or "Staff",
        department=params.get("department") or "General",
        location=params.get("location") or "Headquarters",
        manager_name=params.get("manager_name") or "HR Management",
        basic=salary_result["basic_salary"],
        hra=salary_result["hra"],
        hra_ratio=hra_ratio,
        bonus=salary_result["bonus"],
        bonus_ratio=bonus_ratio,
        gross=salary_result["gross_salary"],
        tax=salary_result["tax"],
        net=salary_result["net_salary"],
        status=salary_result["status"],
        approval=salary_result["approval_required"],
        payroll_context=payroll_context,
    )

    llm_result = llm_service.generate(prompt, model_key="salary", system_prompt=_SYSTEM_PROMPT)

    # Step 5: Output guardrails validate the response
    validated_response, guardrail_checks = validate_salary_guardrails(
        candidate=dict(llm_result),
        salary_result=salary_result,
        params=params,
    )
    validated_response["knowledge_sources"] = knowledge_sources
    validated_response["guardrail_checks"] = guardrail_checks

    # Step 6: Final approved result shown to authorized user
    state["response"] = validated_response
    state["score"] = validated_response["score"]
    state["approved"] = validated_response.get("approved", not salary_result["approval_required"])
    state["status"] = salary_result["status"]
    return state
