VALID_SALARY_STATUSES = {"submitted", "in review", "approved", "rejected", "escalated"}


def validate_salary_components(basic_salary: float, hra: float, bonus: float) -> list[str]:
    issues: list[str] = []

    if basic_salary is None or basic_salary < 0:
        issues.append("basic_salary")
    if hra is None or hra < 0:
        issues.append("hra")
    if bonus is None or bonus < 0:
        issues.append("bonus")

    if basic_salary and basic_salary > 500000:
        issues.append("basic_salary_too_high")
    if hra and hra > 150000:
        issues.append("hra_too_high")
    if bonus and bonus > 100000:
        issues.append("bonus_too_high")

    return issues


def calculate_salary(
    basic_salary: float,
    hra: float,
    bonus: float,
    tax_rate: float = 0.10,
    review_threshold: float = 200000.0,
    escalation_threshold: float = 500000.0,
):
    issues = validate_salary_components(basic_salary, hra, bonus)
    if issues:
        raise ValueError(f"Invalid salary components: {', '.join(issues)}")

    gross_salary = basic_salary + hra + bonus

    if tax_rate < 0 or tax_rate > 0.5:
        raise ValueError("tax_rate must be between 0 and 0.5")

    tax = gross_salary * tax_rate
    net_salary = gross_salary - tax

    status = "approved"
    approval_required = False
    review_reasons: list[str] = []

    if gross_salary >= escalation_threshold:
        status = "escalated"
        approval_required = True
        review_reasons.append("gross_salary_exceeds_escalation_threshold")
    elif gross_salary >= review_threshold:
        status = "in review"
        approval_required = True
        review_reasons.append("gross_salary_requires_manager_approval")

    return {
        "basic_salary": float(basic_salary),
        "hra": float(hra),
        "bonus": float(bonus),
        "gross_salary": float(gross_salary),
        "tax": float(tax),
        "net_salary": float(net_salary),
        "status": status,
        "approval_required": approval_required,
        "review_reasons": review_reasons,
    }

