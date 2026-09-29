import unittest
from unittest.mock import patch

from backend.agents.salary_agent import calculate_employee_salary
from backend.agents.security_agent import run_security_check
from backend.agents.support_agent import create_support_ticket
from backend.services.huggingface_service import _extract_json
from backend.workflows.langgraph_orchestrator import graph


class TestLLMAgents(unittest.TestCase):
    def test_extract_json_handles_markdown_and_types(self):
        markdown_sample = """
        Here is the evaluation:
        ```json
        {
            "score": "88",
            "approved": "true",
            "issues": ["Minor typo in paragraph 2"],
            "recommendations": "Add an example",
            "requires_human_review": "false"
        }
        ```
        """
        extracted = _extract_json(markdown_sample)
        self.assertEqual(extracted["score"], 88)
        self.assertTrue(extracted["approved"])
        self.assertFalse(extracted["requires_human_review"])
        self.assertEqual(extracted["issues"], ["Minor typo in paragraph 2"])
        self.assertEqual(extracted["recommendations"], ["Add an example"])

    @patch("backend.services.llm_service.generate")
    def test_salary_agent_natural_language_extraction(self, mock_generate):
        mock_generate.return_value = {
            "score": 92,
            "approved": True,
            "message": "Compensation package is balanced and well within standard corporate thresholds.",
            "issues": [],
            "recommendations": ["Ensure tax withholding form W-4 is on file."],
            "status": "approved",
            "risk_level": "low",
            "requires_human_review": False,
        }

        state = {
            "user_input": "Please calculate salary for employee Mark EMP-305 with basic ₹70000, HRA ₹14000, and bonus ₹6000",
            "route": "SALARY",
            "response": {},
            "score": 0,
            "approved": False,
            "iteration": 0,
        }
        result = calculate_employee_salary(state)
        resp = result["response"]

        self.assertEqual(resp["employee_id"], "EMP-305")
        self.assertEqual(resp["employee_name"], "Mark")
        self.assertEqual(resp["basic_salary"], 70000.0)
        self.assertEqual(resp["hra"], 14000.0)
        self.assertEqual(resp["bonus"], 6000.0)
        self.assertEqual(resp["gross_salary"], 90000.0)
        self.assertEqual(resp["tax"], 9000.0)
        self.assertEqual(resp["net_salary"], 81000.0)
        self.assertIn("pan", resp)
        self.assertTrue(resp["pan"].endswith("234F"))
        self.assertEqual(result["score"], 92)
        self.assertTrue(result["approved"])

    @patch("backend.services.llm_service.generate")
    def test_security_agent_compliance_rules_and_reasoning(self, mock_generate):
        mock_generate.return_value = {
            "score": 95,
            "approved": True,
            "message": "All mandatory identity credentials and background checks are satisfied.",
            "issues": [],
            "recommendations": ["Schedule routine annual compliance re-check."],
            "status": "approved",
            "risk_level": "low",
            "requires_human_review": False,
        }

        state = {
            "user_input": "Audit security record for EMP-882 passport P1234567 aadhaar 123456789012 address 42 Wallaby Way police cleared",
            "route": "SECURITY",
            "response": {},
            "score": 0,
            "approved": False,
            "iteration": 0,
        }
        result = run_security_check(state)
        resp = result["response"]

        self.assertEqual(resp["employee_id"], "EMP-882")
        self.assertEqual(len(resp["missing_fields"]), 0)
        self.assertEqual(resp["status"], "approved")
        self.assertEqual(result["score"], 95)
        self.assertTrue(result["approved"])

    @patch("backend.services.llm_service.generate")
    def test_support_agent_creates_ticket_with_triage(self, mock_generate):
        mock_generate.return_value = {
            "score": 85,
            "approved": True,
            "message": "Critical networking issue affecting developer VPN access. High impact incident.",
            "issues": ["VPN server connectivity packet loss"],
            "recommendations": ["Restart gateway tunnel", "Failover to secondary concentrator"],
            "status": "submitted",
            "risk_level": "high",
            "requires_human_review": True,
            "suggested_category": "network",
            "suggested_priority": "urgent",
        }

        state = {
            "user_input": "Urgent: VPN server is dropping connections for dev team, contact devops@company.com",
            "route": "SUPPORT",
            "response": {},
            "score": 0,
            "approved": False,
            "iteration": 0,
        }
        result = create_support_ticket(state)
        resp = result["response"]

        self.assertIn("ticket_id", resp)
        self.assertEqual(resp["requester"], "devops@company.com")
        self.assertEqual(resp["category"], "network")
        self.assertEqual(resp["priority"], "urgent")
        self.assertIn("VPN server connectivity packet loss", resp["issues"])

    @patch("backend.services.llm_service.generate")
    def test_langgraph_full_orchestration_blog(self, mock_generate):
        mock_generate.return_value = {
            "score": 88,
            "approved": True,
            "message": "High quality draft on multi-agent architectures with robust technical structure.",
            "issues": [],
            "recommendations": ["Include benchmark graphs before final publishing."],
            "status": "approved",
            "risk_level": "low",
            "requires_human_review": False,
        }

        initial_state = {
            "user_input": "Draft an article about the future of multi-agent architectures in healthcare",
            "route": "",
            "response": {},
            "score": 0,
            "approved": False,
            "iteration": 0,
        }
        final_state = graph.invoke(initial_state)

        self.assertEqual(final_state["route"], "BLOG")
        self.assertEqual(final_state["status"], "completed")
        self.assertEqual(final_state["score"], 88.0)
        self.assertTrue(final_state["approved"])


if __name__ == "__main__":
    unittest.main()
