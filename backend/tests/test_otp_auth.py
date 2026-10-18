import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import _otp_challenges, _otp_send_times, _otp_verify_times
from app.config import settings
from app.main import app


class OtpAuthTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(settings, "auth_enabled", True),
            patch.object(settings, "app_env", "development"),
            patch.object(settings, "secret_key", "test-session-key-with-enough-length"),
            patch.object(settings, "minimoth_api_key", "mm_test_key"),
        ]
        for item in self.patches:
            item.start()
        _otp_challenges.clear()
        _otp_send_times.clear()
        _otp_verify_times.clear()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        _otp_challenges.clear()
        _otp_send_times.clear()
        _otp_verify_times.clear()
        for item in reversed(self.patches):
            item.stop()

    def test_send_otp_uses_provider_and_does_not_expose_challenge_id(self):
        provider = {"otp_id": "secret-challenge-id", "expires_at": "2030-01-01T00:00:00Z"}
        with patch("app.auth.httpx.post") as request:
            request.return_value.is_success = True
            request.return_value.json.return_value = provider
            response = self.client.post("/api/auth/otp/send", json={"phone": "+919876543210"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sent": True, "expires_in": 600, "resend_after": 60})
        self.assertNotIn("secret-challenge-id", response.text)
        self.assertEqual(request.call_args.kwargs["headers"]["X-Api-Key"], "mm_test_key")
        self.assertEqual(request.call_args.kwargs["json"], {"phone": "+919876543210"})

    def test_verification_sets_httponly_session_and_protects_dashboard(self):
        with patch("app.auth.httpx.post") as request:
            request.return_value.is_success = True
            request.return_value.json.return_value = {"otp_id": "otp-123"}
            self.assertEqual(self.client.post("/api/auth/otp/send", json={"phone": "+919876543210"}).status_code, 200)
            request.return_value.json.return_value = {
                    "access_token": "upstream-access-secret",
                    "refresh_token": "upstream-refresh-secret",
                    "identity_id": "identity-123",
                }
            response = self.client.post("/api/auth/otp/verify", json={"phone": "+919876543210", "code": "123456"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("upstream-access-secret", response.text)
        self.assertNotIn("upstream-refresh-secret", response.text)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/api/workspace/documents").status_code, 200)

    def test_invalid_code_is_reported_and_does_not_authenticate(self):
        with patch("app.auth.httpx.post") as request:
            request.return_value.is_success = True
            request.return_value.json.return_value = {"otp_id": "otp-123"}
            self.client.post("/api/auth/otp/send", json={"phone": "+919876543210"})
            request.return_value.is_success = False
            request.return_value.status_code = 400
            response = self.client.post("/api/auth/otp/verify", json={"phone": "+919876543210", "code": "000000"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("invalid or expired", response.json()["detail"])
        self.assertEqual(self.client.get("/api/workspace/documents").status_code, 401)

    def test_expired_challenge_requires_a_new_code(self):
        _otp_challenges["+919876543210"] = {"otp_id": "old", "created_at": time.time() - 601}
        response = self.client.post("/api/auth/otp/verify", json={"phone": "+919876543210", "code": "123456"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Request a new code", response.json()["detail"])

    def test_logout_clears_the_cookie_and_protected_api_returns_401(self):
        with patch("app.auth.httpx.post") as request:
            request.return_value.is_success = True
            request.return_value.json.return_value = {"otp_id": "otp-123"}
            self.client.post("/api/auth/otp/send", json={"phone": "+919876543210"})
            request.return_value.json.return_value = {"access_token": "access", "refresh_token": "refresh"}
            self.client.post("/api/auth/otp/verify", json={"phone": "+919876543210", "code": "123456"})
        self.assertEqual(self.client.get("/api/workspace/documents").status_code, 200)
        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/workspace/documents").status_code, 401)


if __name__ == "__main__":
    unittest.main()
