import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.db import initialize_database, get_db_session
from backend.main import app
from backend.services.ticket_service import create_ticket, get_ticket, list_tickets
from backend.services.workflow_state_service import save_workflow_state, get_workflow_state


class TestPhase3Persistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(self.temp_dir.name, 'test.db')}"
        initialize_database(force=True)
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ticket_persists_in_database(self):
        ticket = create_ticket("Persisted ticket")
        self.assertIsNotNone(ticket)
        self.assertIsNotNone(get_ticket(ticket["ticket_id"]))
        self.assertGreater(len(list_tickets()), 0)

    def test_workflow_state_can_be_saved_and_loaded(self):
        state = save_workflow_state("request-id-1", {"user_input": "blog review", "route": "BLOG", "score": 80, "approved": True})
        self.assertEqual(state["route"], "BLOG")
        loaded = get_workflow_state("request-id-1")
        self.assertEqual(loaded["route"], "BLOG")

    def test_ticket_list_endpoint_is_available(self):
        create_ticket("List test")
        response = self.client.get(
            "/tickets",
            headers={"Authorization": "Bearer admin-demo-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()), 0)


if __name__ == "__main__":
    unittest.main()
