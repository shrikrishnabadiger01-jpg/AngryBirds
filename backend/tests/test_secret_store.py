import unittest
from unittest.mock import patch

from app.config import settings
from app.secret_store import PREFIX, protect, reveal


class SecretStoreTests(unittest.TestCase):
    def test_secret_fields_are_encrypted_and_round_trip(self):
        with patch.object(settings, "secret_key", "stable-test-secret-key-for-fernet"):
            protected = protect("refresh-token-value")
            self.assertTrue(protected.startswith(PREFIX))
            self.assertNotIn("refresh-token-value", protected)
            self.assertEqual(reveal(protected), "refresh-token-value")

    def test_plaintext_records_remain_readable_for_local_migration(self):
        self.assertEqual(reveal("legacy-plaintext"), "legacy-plaintext")


if __name__ == "__main__":
    unittest.main()
