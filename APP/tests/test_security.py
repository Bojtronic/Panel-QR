import unittest

from panelqr import create_app
from panelqr.security import hash_password, verify_password


class PasswordHashTests(unittest.TestCase):
    def test_hash_verifies_the_original_password(self):
        stored_hash = hash_password("UnaClaveLarga-123")

        self.assertTrue(verify_password("UnaClaveLarga-123", stored_hash))
        self.assertFalse(verify_password("otra-clave", stored_hash))

    def test_malformed_hash_is_rejected(self):
        self.assertFalse(verify_password("password", "not-a-valid-hash"))


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "WTF_CSRF_ENABLED": False,
                "UPLOAD_FOLDER": "/tmp/panelqr-test-storage",
            }
        )
        self.client = self.app.test_client()

    def test_health_endpoint_does_not_require_a_database(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_login_page_is_rendered(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Iniciar sesi", response.data)
        self.assertIn(b'name="csrf_token"', response.data)

    def test_login_post_requires_csrf_token(self):
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "csrf-test-key",
                "UPLOAD_FOLDER": "/tmp/panelqr-csrf-test-storage",
            }
        )
        client = app.test_client()

        self.assertEqual(client.get("/login").status_code, 200)
        self.assertEqual(client.post("/login", data={"email": "x", "password": "y"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
