"""Spatial zone and tripwire unit tests without loading the detection model."""
from app.analytics.zones import ZoneEngine, ZoneMap


def test_tripwire_requires_a_finite_segment_crossing():
    zones = ZoneMap({
        "camera_id": "test-camera",
        "tripwires": [{
            "tripwire_id": "entry",
            "event_type": "ENTRY",
            "line": [[5, 0], [5, 10]],
        }],
    })
    engine = ZoneEngine(zones)

    assert engine.crossed_tripwires(
        {"box": [2, 0, 4, 5]},
        {"box": [0, 0, 2, 5]},
    ) == []
    assert engine.crossed_tripwires(
        {"box": [6, 0, 8, 5]},
        {"box": [2, 0, 4, 5]},
    ) == ["ENTRY"]

    zones.tripwires[0]["line"] = [[5, 10], [5, 20]]
    assert engine.crossed_tripwires(
        {"box": [6, 0, 8, 5]},
        {"box": [2, 0, 4, 5]},
    ) == []


def test_slot_containment_respects_canonical_category():
    zones = ZoneMap({
        "camera_id": "test-camera",
        "slots": [{
            "slot_id": "A-01",
            "vehicle_category": "COMPACT_CAR",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        }],
    })

    assert [slot["slot_id"] for slot in zones.containing_slots([20, 20, 40, 80], "COMPACT_CAR")] == ["A-01"]
    assert zones.containing_slots([20, 20, 40, 80], "HEAVY_VEHICLE") == []


if __name__ == "__main__":
    test_tripwire_requires_a_finite_segment_crossing()
    test_slot_containment_respects_canonical_category()
    print("spatial analytics checks passed")
