import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import hash_password
from app.config import settings
from app.config import Settings
from app.main import app


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(settings, "auth_enabled", True),
            patch.object(settings, "app_env", "development"),
            patch.object(settings, "secret_key", "test-session-key-with-enough-length"),
            patch.object(settings, "auth_users_json", json.dumps({
                "reader": {"password_hash": hash_password("reader-pass"), "role": "auditor"},
                "admin": {"password_hash": hash_password("admin-pass"), "role": "admin"},
            })),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches):
            item.stop()

    def test_authentication_required_for_audit_data(self):
        self.assertEqual(self.client.get("/api/audit").status_code, 401)

    def test_auditor_can_read_but_cannot_start_runs_or_list_accounts(self):
        login = self.client.post("/api/auth/login", json={"username": "reader", "password": "reader-pass"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/audit").status_code, 200)
        run = self.client.post("/api/workspace/run", json={"task": "Read the report", "document_id": "project_report"})
        self.assertEqual(run.status_code, 403)
        self.assertEqual(self.client.get("/api/auth/users").status_code, 403)

    def test_admin_account_listing_never_returns_password_hashes(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
        response = self.client.get("/api/auth/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"username": "admin", "role": "admin"}, {"username": "reader", "role": "auditor"}])
        self.assertNotIn("password_hash", response.text)

    def test_policy_inputs_are_enforced_and_confidential_documents_are_not_listed(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
        visible_docs = self.client.get("/api/workspace/documents").json()
        self.assertNotIn("confidential_budget", {doc["id"] for doc in visible_docs})
        rejected = self.client.post("/api/workspace/run", json={
            "task": "Read the report",
            "document_id": "project_report",
            "allowed_documents": ["confidential_budget"],
        })
        self.assertEqual(rejected.status_code, 422)

    def test_configurable_policy_is_recorded_and_applied(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
        with patch("agent.runner.get_minimoth_client", return_value=(None, None)):
            response = self.client.post("/api/workspace/run", json={
                "task": "Summarize the report and send an update",
                "document_id": "project_report",
                "allow_email": True,
                "allowed_documents": ["project_report", "report_training_quote"],
                "allowed_recipients": ["manager@example.com"],
                "max_emails": 0,
                "required_subject": "Exact approved subject",
            })
        self.assertEqual(response.status_code, 200)
        run = response.json()
        self.assertEqual(run["policy"]["allowed_documents"], ["project_report", "report_training_quote"])
        self.assertEqual(run["policy"]["max_emails"], 0)
        self.assertEqual(run["policy"]["required_subject"], "Exact approved subject")
        self.assertEqual(run["outbox"], [])
        self.assertTrue(any(event["decision"] == "BLOCK" for event in run["audit"]))
        history = self.client.get("/api/audit", params={"source": "run", "decision": "BLOCK", "q": "Summarize the report"})
        self.assertGreater(history.json()["total"], 0)
        csv_export = self.client.get("/api/audit/export", params={"format": "csv", "source": "run"})
        self.assertEqual(csv_export.status_code, 200)
        self.assertTrue(csv_export.text.startswith("id,timestamp,source"))
        json_export = self.client.get("/api/audit/export", params={"format": "json"})
        self.assertEqual(json_export.headers["content-type"], "application/json")

    def test_production_settings_refuse_to_start_without_auth(self):
        with self.assertRaises(ValueError):
            Settings(app_env="production", auth_enabled=False, _env_file=None)


if __name__ == "__main__":
    unittest.main()
