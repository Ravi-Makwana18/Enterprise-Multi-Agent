VALID_SECURITY_STATUSES = {"submitted", "in review", "approved", "rejected", "escalated"}
REQUIRED_FIELDS = ["passport", "aadhaar", "address", "police_verification"]


def check_missing_fields(record):
    missing_fields = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if not value:
            missing_fields.append(field)
    return missing_fields


def validate_security_record(record: dict) -> dict:
    missing_fields = check_missing_fields(record)
    issues: list[str] = []

    if record.get("aadhaar"):
        aadhaar = str(record["aadhaar"]).replace(" ", "")
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            issues.append("aadhaar_format_invalid")

    if record.get("passport"):
        passport = str(record["passport"]).strip()
        if len(passport) < 6:
            issues.append("passport_too_short")

    if record.get("police_verification") == "pending":
        issues.append("police_verification_pending")

    status = "approved"
    approval_required = False

    if missing_fields or issues:
        status = "in review"
        approval_required = True

    if len(missing_fields) >= 2 or len(issues) >= 2:
        status = "escalated"
        approval_required = True

    return {
        "employee_id": record.get("employee_id"),
        "employee_name": record.get("employee_name"),
        "missing_fields": missing_fields,
        "issues": issues,
        "status": status,
        "approval_required": approval_required,
        "human_approval_required": approval_required,
        "workflow": "security",
    }


def evaluate_security_check(record: dict) -> dict:
    return validate_security_record(record)


def approve_security_record(record: dict, approver: str) -> dict:
    result = validate_security_record(record)
    if result["status"] in {"approved", "in review"}:
        result["status"] = "approved"
        result["approval_required"] = False
        result["human_approval_required"] = False
        result["approved_by"] = approver
        result["decision"] = "approved"
    return result