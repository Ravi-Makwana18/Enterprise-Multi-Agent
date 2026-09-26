import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.core.pii import redact_pii


class TestPhase2Security(unittest.TestCase):
    def setUp(self):
        from backend.main import rate_limit_store

        rate_limit_store.clear()
        self.client = TestClient(app)

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_admin_endpoints_require_auth(self):
        response = self.client.get("/diagnostics")
        self.assertEqual(response.status_code, 401)

    def test_user_token_cannot_access_admin_endpoints(self):
        response = self.client.get(
            "/diagnostics",
            headers={"Authorization": "Bearer user-demo-token"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_token_can_access_admin_endpoints(self):
        response = self.client.get(
            "/diagnostics",
            headers={"Authorization": "Bearer admin-demo-token"},
        )
        self.assertEqual(response.status_code, 200)

    def test_rate_limiter_blocks_excess_requests(self):
        from backend.main import settings

        settings.rate_limit_requests_per_minute = 1
        client = TestClient(app)

        first = client.get("/health", headers={"Authorization": "Bearer user-demo-token"})
        second = client.get("/health", headers={"Authorization": "Bearer user-demo-token"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_pii_redaction_masks_email_and_phone(self):
        result = redact_pii("Contact me at ravi@example.com or 555-123-4567")
        self.assertIn("***@example.com", result)
        self.assertIn("***-***-4567", result)


if __name__ == "__main__":
    unittest.main()
