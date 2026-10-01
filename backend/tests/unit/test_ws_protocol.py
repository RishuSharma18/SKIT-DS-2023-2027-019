import unittest
import json

class TestWebSocketProtocolSerialization(unittest.TestCase):
    """Unit tests verifying WebSocket payload schemas and broadcast message serialization."""

    @staticmethod
    def format_event_message(event_name: str, payload: dict) -> str:
        message = {
            "event": event_name,
            "data": payload
        }
        return json.dumps(message, default=str)

    def test_alert_event_serialization(self):
        payload = {
            "alert_id": "test-uuid-1234",
            "alert_type": "WRONG_PARKING",
            "severity": "MEDIUM",
            "plate_number": "RJ14AB1234",
            "slot_id": "B-02",
            "camera_id": "cam-2",
            "is_acknowledged": False
        }
        msg = self.format_event_message("alert:new", payload)
        parsed = json.loads(msg)

        self.assertEqual(parsed["event"], "alert:new")
        self.assertEqual(parsed["data"]["alert_type"], "WRONG_PARKING")
        self.assertFalse(parsed["data"]["is_acknowledged"])

    def test_slot_update_serialization(self):
        slots_payload = [
            {"slot_id": "A-01", "status": "OCCUPIED"},
            {"slot_id": "A-02", "status": "AVAILABLE"}
        ]
        msg = self.format_event_message("slots:update", slots_payload)
        parsed = json.loads(msg)

        self.assertEqual(parsed["event"], "slots:update")
        self.assertEqual(len(parsed["data"]), 2)
        self.assertEqual(parsed["data"][0]["status"], "OCCUPIED")

if __name__ == "__main__":
    unittest.main()
