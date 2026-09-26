import unittest

from backend.workflows.langgraph_orchestrator import (
    classify_request,
    route_decision,
    execute_with_retry,
    normalize_route,
)


class TestLangGraphOrchestrator(unittest.TestCase):
    def test_classify_request_sets_deterministic_route(self):
        state = {"user_input": "salary review for employee", "route": "", "response": {}, "score": 0, "approved": False, "iteration": 0}
        result = classify_request(state)
        self.assertEqual(result["route"], "SALARY")
        self.assertIn("status", result["response"])

    def test_route_decision_uses_standardized_values(self):
        self.assertEqual(route_decision({"route": "salary"}), "salary_agent")
        self.assertEqual(route_decision({"route": "BLOG"}), "blog_agent")
        self.assertEqual(route_decision({"route": "unknown"}), "support_agent")

    def test_execute_with_retry_retries_transient_errors(self):
        attempts = {"count": 0}

        def flaky_step(state):
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise RuntimeError("transient")
            state["response"] = {"status": "ok"}
            return state

        state = {"user_input": "ping", "route": "SUPPORT", "response": {}, "score": 0, "approved": False, "iteration": 0, "execution_history": []}
        result = execute_with_retry("support_agent", state, flaky_step, max_retries=2)
        self.assertEqual(result["response"]["status"], "ok")
        self.assertEqual(attempts["count"], 2)

    def test_normalize_route_handles_unknown_routes(self):
        self.assertEqual(normalize_route("security"), "SECURITY")
        self.assertEqual(normalize_route("unknown"), "SUPPORT")


if __name__ == "__main__":
    unittest.main()
