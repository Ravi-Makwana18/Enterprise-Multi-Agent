import unittest

from fastapi.testclient import TestClient

from backend.main import app


class TestPhase1Foundation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint_returns_status(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("app", data)

    def test_diagnostics_endpoint_exists(self):
        response = self.client.get(
            "/diagnostics",
            headers={"Authorization": "Bearer admin-demo-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("environment", data)
        self.assertIn("checks", data)

    def test_invalid_chat_request_is_rejected(self):
        response = self.client.post(
            "/chat",
            json={"message": "   "},
            headers={"Authorization": "Bearer user-demo-token"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
