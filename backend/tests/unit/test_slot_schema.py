import unittest
import json

class TestParkingSlotSchema(unittest.TestCase):
    """Unit tests validating parking slot schema boundaries and category rules."""

    def setUp(self):
        self.valid_categories = {"TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"}
        self.valid_statuses = {"AVAILABLE", "RESERVED", "OCCUPIED", "VIOLATION"}

    def validate_slot_dict(self, slot: dict):
        self.assertIn("slot_id", slot)
        self.assertIn("zone", slot)
        self.assertIn("allowed_category", slot)
        self.assertIn("status", slot)
        self.assertIn("polygon_coords", slot)

        self.assertIn(slot["allowed_category"], self.valid_categories)
        self.assertIn(slot["status"], self.valid_statuses)

        coords = slot["polygon_coords"]
        self.assertIsInstance(coords, list)
        self.assertGreaterEqual(len(coords), 3, "Polygon must contain at least 3 vertices")
        for pt in coords:
            self.assertEqual(len(pt), 2, "Each coordinate vertex must have (x, y)")
            self.assertGreaterEqual(pt[0], 0, "X coordinate must be non-negative")
            self.assertGreaterEqual(pt[1], 0, "Y coordinate must be non-negative")

    def test_sample_slot_validations(self):
        sample = {
            "slot_id": "A-01",
            "zone": "ZONE-A",
            "allowed_category": "COMPACT_CAR",
            "status": "AVAILABLE",
            "polygon_coords": [[100, 200], [200, 200], [200, 350], [100, 350]],
            "current_track_id": None
        }
        self.validate_slot_dict(sample)

    def test_invalid_category_rejected(self):
        invalid_sample = {
            "slot_id": "A-02",
            "zone": "ZONE-A",
            "allowed_category": "AIRPLANE",
            "status": "AVAILABLE",
            "polygon_coords": [[100, 100], [150, 100], [150, 150]]
        }
        with self.assertRaises(AssertionError):
            self.validate_slot_dict(invalid_sample)

    def test_degenerate_polygon_rejected(self):
        degenerate_sample = {
            "slot_id": "A-03",
            "zone": "ZONE-A",
            "allowed_category": "TWO_WHEELER",
            "status": "AVAILABLE",
            "polygon_coords": [[100, 100], [200, 200]]  # Only 2 points
        }
        with self.assertRaises(AssertionError):
            self.validate_slot_dict(degenerate_sample)

if __name__ == "__main__":
    unittest.main()
