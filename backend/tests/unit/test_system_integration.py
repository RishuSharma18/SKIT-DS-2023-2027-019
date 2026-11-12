import unittest
from datetime import datetime, timezone, timedelta

class TestSystemIntegrationLifecycle(unittest.TestCase):
    """End-to-end multi-stage simulation of parking lifecycle."""

    def setUp(self):
        self.slots = {
            "A-01": {"status": "AVAILABLE", "category": "COMPACT_CAR"},
            "A-02": {"status": "AVAILABLE", "category": "TWO_WHEELER"}
        }
        self.sessions = {}
        self.alerts = []

    def simulate_entry(self, track_id: int, category: str):
        # 1. Allocate slot
        allocated_slot = None
        for s_id, slot in self.slots.items():
            if slot["status"] == "AVAILABLE" and slot["category"] == category:
                slot["status"] = "RESERVED"
                allocated_slot = s_id
                break

        session = {
            "track_id": track_id,
            "category": category,
            "assigned_slot_id": allocated_slot,
            "actual_slot_id": None,
            "status": "ACTIVE",
            "entry_time": datetime.now(timezone.utc)
        }
        self.sessions[track_id] = session
        return session

    def simulate_parked(self, track_id: int, slot_id: str):
        session = self.sessions[track_id]
        session["actual_slot_id"] = slot_id
        self.slots[slot_id]["status"] = "OCCUPIED"

    def simulate_exit(self, track_id: int):
        session = self.sessions[track_id]
        session["status"] = "COMPLETED"
        if session["actual_slot_id"]:
            self.slots[session["actual_slot_id"]]["status"] = "AVAILABLE"

    def test_full_vehicle_lifecycle(self):
        track_id = 701
        # Step 1: Entry
        session = self.simulate_entry(track_id, "COMPACT_CAR")
        self.assertEqual(session["assigned_slot_id"], "A-01")
        self.assertEqual(self.slots["A-01"]["status"], "RESERVED")

        # Step 2: Parked
        self.simulate_parked(track_id, "A-01")
        self.assertEqual(self.slots["A-01"]["status"], "OCCUPIED")

        # Step 3: Exit
        self.simulate_exit(track_id)
        self.assertEqual(session["status"], "COMPLETED")
        self.assertEqual(self.slots["A-01"]["status"], "AVAILABLE")

if __name__ == "__main__":
    unittest.main()
