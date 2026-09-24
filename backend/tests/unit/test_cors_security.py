import unittest

class TestCorsAndSecurityMiddleware(unittest.TestCase):
    """Unit tests for CORS security origin resolution and API key authorization headers."""

    ALLOWED_ORIGINS = {
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    }

    VALID_API_KEYS = {"dev-key", "prod-edge-camera-key-2026"}

    def is_origin_allowed(self, origin: str) -> bool:
        if not origin:
            return True  # Direct server-to-server or curl
        return origin.strip().rstrip("/") in self.ALLOWED_ORIGINS

    def is_api_key_valid(self, key_header: str) -> bool:
        if not key_header:
            return False
        return key_header.strip() in self.VALID_API_KEYS

    def test_allowed_cors_origins(self):
        self.assertTrue(self.is_origin_allowed("http://localhost:5173"))
        self.assertTrue(self.is_origin_allowed("http://localhost:3000/"))
        self.assertTrue(self.is_origin_allowed(None))

    def test_disallowed_cors_origins(self):
        self.assertFalse(self.is_origin_allowed("http://malicious-site.com"))
        self.assertFalse(self.is_origin_allowed("http://localhost:8080"))

    def test_api_key_header_verification(self):
        self.assertTrue(self.is_api_key_valid("dev-key"))
        self.assertTrue(self.is_api_key_valid("prod-edge-camera-key-2026"))
        self.assertFalse(self.is_api_key_valid("wrong-key"))
        self.assertFalse(self.is_api_key_valid(""))
        self.assertFalse(self.is_api_key_valid(None))

if __name__ == "__main__":
    unittest.main()
