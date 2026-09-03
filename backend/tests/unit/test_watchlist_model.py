import unittest
import re

class TestWatchlistModel(unittest.TestCase):
    """Unit tests verifying license plate normalization and watchlist query rules."""

    @staticmethod
    def normalize_plate(plate: str) -> str:
        """Normalizes vehicle license plate: uppercase, strips whitespace and hyphens."""
        if not plate:
            return ""
        return re.sub(r"[^A-Z0-9]", "", plate.upper().strip())

    @staticmethod
    def is_valid_plate_format(plate: str) -> bool:
        """Validates Indian vehicle registration plate pattern:
        2 letters (State) + 2 digits (District) + optional 1-3 letters + 4 digits.
        """
        pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$"
        return bool(re.match(pattern, plate))

    def test_plate_normalization(self):
        cases = [
            ("rj-14 ab 1234", "RJ14AB1234"),
            ("DL 01-XY-9999", "DL01XY9999"),
            ("hr26dk4400", "HR26DK4400"),
            (" UP-32-EF-5555 ", "UP32EF5555"),
            ("mh 02 cr 7890", "MH02CR7890")
        ]
        for raw, expected in cases:
            self.assertEqual(self.normalize_plate(raw), expected)

    def test_plate_pattern_matching(self):
        valid_plates = ["RJ14AB1234", "DL01XY9999", "HR26DK4400", "MH12Q1234", "KA051234"]
        for p in valid_plates:
            self.assertTrue(self.is_valid_plate_format(p), f"Expected {p} to be valid")

    def test_invalid_plate_patterns(self):
        invalid_plates = ["1234RJ", "RJ14AB12345", "INVALID", "", "A123"]
        for p in invalid_plates:
            self.assertFalse(self.is_valid_plate_format(p), f"Expected {p} to be invalid")

if __name__ == "__main__":
    unittest.main()
