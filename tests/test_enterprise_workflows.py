import unittest

from backend.services.salary_service import calculate_salary
from backend.services.security_service import evaluate_security_check
from backend.services.ticket_service import create_ticket, update_ticket_status


class TestEnterpriseWorkflows(unittest.TestCase):
    def test_salary_engine_validates_and_approves_standard_value(self):
        result = calculate_salary(50000, 10000, 5000)
        self.assertEqual(result["gross_salary"], 65000.0)
        self.assertEqual(result["status"], "approved")
        self.assertFalse(result["approval_required"])

    def test_salary_engine_escalates_high_risk_outlier(self):
        result = calculate_salary(500000, 20000, 40000)
        self.assertEqual(result["status"], "escalated")
        self.assertTrue(result["approval_required"])

    def test_security_check_requires_human_approval_on_missing_fields(self):
        record = {
            "employee_id": "EMP-001",
            "employee_name": "Ravi",
            "passport": "",
            "aadhaar": "1234",
            "address": "",
            "police_verification": "pending",
        }

        result = evaluate_security_check(record)
        self.assertEqual(result["status"], "escalated")
        self.assertIn("passport", result["missing_fields"])
        self.assertTrue(result["approval_required"])

    def test_ticket_case_management_tracks_lifecycle(self):
        ticket = create_ticket(
            "Payroll correction for Q3",
            category="payroll",
            priority="high",
            requester="manager@company.com",
        )
        self.assertEqual(ticket["status"], "submitted")

        updated = update_ticket_status(ticket["ticket_id"], "approved")
        self.assertEqual(updated["status"], "approved")

    def test_invalid_ticket_status_is_rejected(self):
        ticket = create_ticket("New case")
        with self.assertRaises(ValueError):
            update_ticket_status(ticket["ticket_id"], "not-a-valid-status")


if __name__ == "__main__":
    unittest.main()
