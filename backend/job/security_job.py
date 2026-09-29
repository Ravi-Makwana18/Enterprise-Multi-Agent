import logging
from datetime import datetime, timezone
from typing import Any

from backend.agents.security_agent import run_security_check
from backend.services.employee_service import list_employees
from backend.services.review_service import create_review

logger = logging.getLogger(__name__)


def execute() -> dict[str, Any]:
    """
    Scheduled Automation:
    Scans all enterprise employees for missing HR/security documentation
    and notifies HR / administrators by generating audit reviews and tracking alerts.
    """
    logger.info("Executing scheduled security background check automation...")
    from backend.db import initialize_database
    from backend.services.employee_service import seed_default_employees
    initialize_database()
    try:
        seed_default_employees()
    except Exception:
        pass
    employees = list_employees()
    scanned_count = len(employees)
    flagged = []
    notifications = []

    for emp in employees:
        emp_id = emp["employee_id"]
        emp_name = emp["employee_name"]

        state = {
            "user_input": f"Perform scheduled background check audit for {emp_name} ({emp_id})",
            "route": "SECURITY",
            "employee_id": emp_id,
            "employee_name": emp_name,
            "user_role": "admin",
            "user_name": "System Scheduler",
            "response": {},
            "score": 0,
            "approved": False,
            "iteration": 0,
        }

        try:
            result = run_security_check(state)
            resp = result.get("response", {})
            missing = resp.get("missing_fields", [])
            issues = resp.get("issues", [])
            status = resp.get("status", "approved")
            requires_review = resp.get("approval_required", False) or resp.get("requires_human_review", False)

            if missing or requires_review or status != "approved":
                flagged.append({
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "status": status,
                    "missing_fields": missing,
                    "issues": issues,
                    "score": result.get("score", 0),
                })

                review_title = f"[SECURITY AUDIT] {emp_name} ({emp_id}) - Missing Credentials Flagged"
                review_content = (
                    f"Scheduled background verification detected missing data:\n"
                    f"• Missing Fields: {', '.join(missing) if missing else 'None'}\n"
                    f"• Compliance Issues: {'; '.join(issues) if issues else 'None'}\n"
                    f"• Audit Status: {status.upper()}"
                )
                try:
                    create_review({
                        "title": review_title,
                        "reviewer": "Automated Security Scheduler (Pending Review)",
                        "review_type": "SECURITY",
                        "content": review_content,
                        "status": "pending",
                        "score": float(result.get("score") or 0.0),
                        "approved": False,
                        "issues": issues,
                        "recommendations": resp.get("recommendations", ["Notify employee to submit missing documents"]),
                    })
                    notifications.append(f"Notification queued for HR regarding {emp_name} ({emp_id})")
                except Exception as rev_err:
                    logger.warning("Failed to queue review notification: %s", rev_err)

        except Exception as exc:
            logger.error("Error evaluating security check for %s: %s", emp_id, exc)

    report = {
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_employees_scanned": scanned_count,
        "compliant_count": scanned_count - len(flagged),
        "flagged_count": len(flagged),
        "flagged_employees": flagged,
        "notifications": notifications,
    }
    logger.info("Scheduled security check completed: %d scanned, %d flagged", scanned_count, len(flagged))
    return report


if __name__ == "__main__":
    report = execute()
    print(report)