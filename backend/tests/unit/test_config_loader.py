import unittest
import os

class TestConfigLoader(unittest.TestCase):
    """Unit tests for environment variable loading, defaults, and type casting."""

    @staticmethod
    def parse_bool(val: str, default: bool = False) -> bool:
        if val is None:
            return default
        return str(val).strip().lower() in ("true", "1", "yes", "t", "on")

    @staticmethod
    def parse_int(val: str, default: int, min_val: int = 1) -> int:
        try:
            parsed = int(val)
            return max(min_val, parsed)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def mask_connection_string(conn_str: str) -> str:
        """Masks passwords in database connection URLs for safe logging."""
        if "://" in conn_str and "@" in conn_str:
            prefix, rest = conn_str.split("://", 1)
            auth, host_path = rest.split("@", 1)
            if ":" in auth:
                user = auth.split(":", 1)[0]
                return f"{prefix}://{user}:***@{host_path}"
        return conn_str

    def test_boolean_parsing(self):
        self.assertTrue(self.parse_bool("True"))
        self.assertTrue(self.parse_bool("1"))
        self.assertTrue(self.parse_bool("yes"))
        self.assertFalse(self.parse_bool("False"))
        self.assertFalse(self.parse_bool("0"))
        self.assertFalse(self.parse_bool("no"))
        self.assertTrue(self.parse_bool(None, default=True))

    def test_integer_parsing_bounds(self):
        self.assertEqual(self.parse_int("60", default=30), 60)
        self.assertEqual(self.parse_int("-5", default=60, min_val=10), 10)
        self.assertEqual(self.parse_int("invalid", default=100), 100)

    def test_secret_masking(self):
        raw_url = "postgresql://postgres:SuperSecretPassword123@localhost:5432/cctv_parking"
        masked = self.mask_connection_string(raw_url)
        self.assertNotIn("SuperSecretPassword123", masked)
        self.assertIn("postgres:***", masked)
        self.assertIn("@localhost:5432/cctv_parking", masked)

if __name__ == "__main__":
    unittest.main()
