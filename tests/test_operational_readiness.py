import unittest

from fastapi.testclient import TestClient

from backend.main import app


class TestOperationalReadiness(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_emits_trace_header(self):
        response = self.client.get(
            "/health",
            headers={"X-Trace-Id": "ops-trace-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Trace-Id"), "ops-trace-123")

    def test_metrics_endpoint_returns_runtime_data(self):
        self.client.get("/health")
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("request_totals", data)
        self.assertIn("latency_summary", data)

    def test_alerts_endpoint_is_available(self):
        self.client.get("/health")
        response = self.client.get("/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("alerts", data)


if __name__ == "__main__":
    unittest.main()
