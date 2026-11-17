import sys
import os
import asyncio
import tempfile
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import JSON

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
test_db = tempfile.NamedTemporaryFile(prefix="cctv-backend-test-", suffix=".db", delete=False)
test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.name}"

from app.config import settings
settings.ENABLE_OVERSTAY_WORKER = False

import httpx
from app.main import app
from app.database import SessionLocal, engine, init_db
from app.models.parking_slot import ParkingSlot
from app.models.vehicle_session import VehicleSession
from app.models.watchlist import Watchlist
from app.models.alert import Alert
from app.services.redis_service import redis_service
from app.services.overstay_worker import check_active_sessions_for_overstay
sys.path.insert(0, str(backend_dir / "scripts"))
from sync_camera_zones import sync_slots

def setup_data():
    init_db()
    db = SessionLocal()
    try:
        db.query(Alert).delete()
        db.query(VehicleSession).delete()
        db.query(ParkingSlot).delete()
        db.query(Watchlist).delete()

        db.add_all([
            ParkingSlot(
                slot_id="A-01",
                zone="ZONE-A",
                allowed_category="TWO_WHEELER",
                status="AVAILABLE",
                polygon_coords=[[50, 100], [120, 100], [120, 220], [50, 220]],
            ),
            ParkingSlot(
                slot_id="A-02",
                zone="ZONE-A",
                allowed_category="COMPACT_CAR",
                status="AVAILABLE",
                polygon_coords=[[150, 100], [220, 100], [220, 220], [150, 220]],
            ),
            ParkingSlot(
                slot_id="B-01",
                zone="ZONE-B",
                allowed_category="SUV_SEDAN",
                status="AVAILABLE",
                polygon_coords=[[250, 100], [320, 100], [320, 220], [250, 220]],
            ),
            ParkingSlot(
                slot_id="C-01",
                zone="ZONE-C",
                allowed_category="HEAVY_VEHICLE",
                status="AVAILABLE",
                polygon_coords=[[350, 100], [420, 100], [420, 220], [350, 220]],
            ),
            ParkingSlot(
                slot_id="UNMAPPED-01",
                zone="UNMAPPED",
                allowed_category="COMPACT_CAR",
                status="AVAILABLE",
                polygon_coords=JSON.NULL,
            ),
        ])
        db.add(Watchlist(plate_number="RJ14AB1234", reason="STOLEN", is_active=True))
        db.commit()
        redis_service.populate_watchlist_cache({"RJ14AB1234"})
    finally:
        db.close()

async def run_async_tests():
    setup_data()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("Running Test 1: OpenAPI docs generated at /docs & /openapi.json...", flush=True)
        res = await client.get("/openapi.json")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        schema = res.json()
        assert "/api/v1/ai-events" in schema["paths"]
        assert "/api/v1/slots/allocate" in schema["paths"]
        assert "/api/v1/watchlist" in schema["paths"]
        assert "/api/v1/sessions" in schema["paths"]
        assert "/api/v1/alerts" in schema["paths"]
        assert "/api/v1/cameras/{camera_id}/zones" in schema["paths"]
        assert "/api/v1/ocr/plate" in schema["paths"]
        print("  -> PASSED: OpenAPI schema validated.", flush=True)

        print("Running Test 1a: Database health and authenticated ingestion...", flush=True)
        health = await client.get("/api/health")
        assert health.status_code == 200 and health.json()["ok"] is True
        assert health.json()["database"] == "sqlite"
        unauthorized = await client.post("/api/v1/ai-events", json={"type": "entry"})
        assert unauthorized.status_code == 401
        legacy_unauthorized = await client.post("/api/events", json={"type": "entry"})
        assert legacy_unauthorized.status_code == 401
        zones = await client.get(
            "/api/v1/cameras/cam-1/zones",
            headers={"x-api-key": "dev-key"},
        )
        assert zones.status_code == 200
        assert (await client.get("/api/v1/cameras/cam-1/zones")).status_code == 401
        zone_data = zones.json()
        assert zone_data["camera_id"] == "cam-1"
        assert any(slot["slot_id"] == "A-01" for slot in zone_data["slots"])

        print("Running Test 1b: Plate OCR upload proxy and validation...", flush=True)
        from unittest.mock import AsyncMock, patch
        ocr_result = {
            "success": True,
            "plate_detected": True,
            "text": "RJ14 AB 1234",
            "raw_text": "RJ14 AB 1234",
            "normalized_text": "RJ14AB1234",
            "confidence": 0.92,
            "is_low_confidence": False,
            "candidates": [{"text": "RJ14 AB 1234", "confidence": 0.92}],
            "error": None,
        }
        with patch(
            "app.api.v1.ocr.forward_plate_image",
            new=AsyncMock(return_value=httpx.Response(200, json=ocr_result)),
        ) as ocr_forward:
            ocr_response = await client.post(
                "/api/v1/ocr/plate",
                files={"file": ("plate.jpg", b"test image bytes", "image/jpeg")},
            )
        assert ocr_response.status_code == 200
        assert ocr_response.json()["normalized_text"] == "RJ14AB1234"
        ocr_forward.assert_awaited_once()

        rejected_upload = await client.post(
            "/api/v1/ocr/plate",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        assert rejected_upload.status_code == 415
        print("  -> PASSED: Backend OCR proxy forwards uploads and rejects unsupported types.", flush=True)

        configured_slots = await client.get("/api/v1/slots?configured_only=true")
        assert configured_slots.status_code == 200 and len(configured_slots.json()) == 4
        legacy_configured_slots = await client.get("/api/slots?configured_only=true")
        assert legacy_configured_slots.status_code == 200 and len(legacy_configured_slots.json()) == 4

        db = SessionLocal()
        now = datetime.now(timezone.utc)
        db.add_all([
            VehicleSession(
                session_id="metrics-active",
                track_id=9001,
                vehicle_category="COMPACT_CAR",
                status="ACTIVE",
                entry_time=now,
            ),
            VehicleSession(
                session_id="metrics-overstay",
                track_id=9002,
                vehicle_category="SUV_SEDAN",
                status="OVERSTAY",
                entry_time=now,
            ),
            VehicleSession(
                session_id="metrics-completed",
                track_id=9003,
                vehicle_category="TWO_WHEELER",
                status="COMPLETED",
                entry_time=now,
            ),
            Alert(
                alert_id="metrics-open-alert",
                alert_type="WRONG_PARKING",
                severity="MEDIUM",
                is_acknowledged=False,
                created_at=now,
            ),
            Alert(
                alert_id="metrics-acknowledged-alert",
                alert_type="OVERSTAY",
                severity="LOW",
                is_acknowledged=True,
                created_at=now,
            ),
        ])
        db.commit()
        db.close()
        dashboard_stats = await client.get("/api/stats")
        assert dashboard_stats.status_code == 200
        metrics = dashboard_stats.json()
        versioned_stats = await client.get("/api/v1/stats")
        assert versioned_stats.status_code == 200
        assert versioned_stats.json() == metrics
        assert metrics["totalCapacity"] == 4
        assert metrics["availableSlots"] == 4
        assert metrics["availableByCategory"] == {
            "TWO_WHEELER": 1,
            "COMPACT_CAR": 1,
            "SUV_SEDAN": 1,
            "HEAVY_VEHICLE": 1,
        }
        assert metrics["activeVehicles"] == 2
        assert metrics["totalAlerts"] == 2
        assert metrics["openAlerts"] == 1
        print("  -> PASSED: Health, auth, camera zones, and configured-space dashboard metrics verified.", flush=True)

        print("Running Test 2: Smart Slot Allocation & Fallback Hierarchy...", flush=True)
        # Exact match for TWO_WHEELER
        r1 = await client.post("/api/v1/slots/allocate", json={"vehicle_category": "TWO_WHEELER"})
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["recommended_slot_id"] == "A-01", f"Got {d1}"
        assert d1["status"] == "RESERVED"

        # Fallback to COMPACT_CAR since A-01 is RESERVED
        r2 = await client.post("/api/v1/slots/allocate", json={"vehicle_category": "TWO_WHEELER"})
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["recommended_slot_id"] == "A-02", f"Got {d2}"
        print("  -> PASSED: Exact matching and fallback allocation verified.", flush=True)

        db = SessionLocal()
        db.add_all([
            ParkingSlot(
                slot_id="NEAR-FAR",
                camera_id="cam-nearest",
                zone="A",
                allowed_category="COMPACT_CAR",
                polygon_coords=[[990, 990], [1010, 990], [1010, 1010], [990, 1010]],
            ),
            ParkingSlot(
                slot_id="NEAR-CLOSE",
                camera_id="cam-nearest",
                zone="Z",
                allowed_category="COMPACT_CAR",
                polygon_coords=[[0, 0], [20, 0], [20, 20], [0, 20]],
            ),
        ])
        db.commit()
        db.close()
        nearest = await client.post(
            "/api/v1/slots/allocate",
            json={
                "vehicle_category": "COMPACT_CAR",
                "camera_id": "cam-nearest",
                "reference_point": [10, 10],
            },
        )
        assert nearest.status_code == 200
        assert nearest.json()["recommended_slot_id"] == "NEAR-CLOSE"
        assert nearest.json()["camera_id"] == "cam-nearest"

        db = SessionLocal()
        db.add(ParkingSlot(
            slot_id="UNMAPPED-CAR",
            camera_id="cam-unmapped",
            zone="U",
            allowed_category="COMPACT_CAR",
            status="AVAILABLE",
        ))
        db.commit()
        db.close()
        unmapped_allocation = await client.post(
            "/api/v1/slots/allocate",
            json={"vehicle_category": "COMPACT_CAR", "camera_id": "cam-unmapped"},
        )
        assert unmapped_allocation.status_code == 200
        assert unmapped_allocation.json()["recommended_slot_id"] is None
        print("  -> PASSED: Geometric nearest-slot selection verified.", flush=True)

        print("Running Test 3: AI Event Ingestion & Idempotency...", flush=True)
        ev_payload = {
            "type": "entry",
            "trackId": 501,
            "vehicleType": "COMPACT_CAR",
            "cameraId": "cam-1"
        }
        r_entry = await client.post("/api/v1/ai-events", json=ev_payload, headers={"x-api-key": "dev-key"})
        assert r_entry.status_code == 201
        d_entry = r_entry.json()
        assert d_entry["success"] is True
        assert d_entry["session"]["track_id"] == 501

        # Duplicate frame (idempotency check)
        r_dup = await client.post("/api/v1/ai-events", json=ev_payload, headers={"x-api-key": "dev-key"})
        assert r_dup.status_code == 201
        d_dup = r_dup.json()
        assert "Duplicate entry frame ignored" in d_dup["message"]

        db = SessionLocal()
        assert db.query(VehicleSession).filter(VehicleSession.track_id == 501).count() == 1
        db.close()
        print("  -> PASSED: Event entry and idempotency verified.", flush=True)

        print("Running Test 3a: Canonical AI event and late plate enrichment...", flush=True)
        canonical_entry = await client.post("/api/v1/ai-events", json={
            "event_id": "event-cam2-entry",
            "event_type": "ENTRY",
            "track_id": 602,
            "vehicle_category": "COMPACT_CAR",
            "camera_id": "cam-2",
            "timestamp": "2026-11-17T00:00:00Z",
        }, headers={"x-api-key": "dev-key"})
        assert canonical_entry.status_code == 201
        assert canonical_entry.json()["event_type"] == "entry"

        late_plate = await client.post("/api/v1/ai-events", json={
            "event_type": "ENTRY",
            "track_id": 602,
            "camera_id": "cam-2",
            "plate_number": "RJ14AB1234",
        }, headers={"x-api-key": "dev-key"})
        assert late_plate.status_code == 201
        assert late_plate.json()["session"]["plate_number"] == "RJ14AB1234"
        assert late_plate.json()["alert"]["alert_type"] == "STOLEN_VEHICLE"

        same_track_other_camera = await client.post("/api/v1/ai-events", json={
            "event_type": "ENTRY",
            "track_id": 602,
            "camera_id": "cam-3",
            "vehicle_category": "COMPACT_CAR",
        }, headers={"x-api-key": "dev-key"})
        assert same_track_other_camera.status_code == 201
        db = SessionLocal()
        assert db.query(VehicleSession).filter(VehicleSession.track_id == 602).count() == 2
        db.close()

        alert_event = await client.post("/api/v1/ai-events", json={
            "event_id": "event-cam2-alert",
            "event_type": "ALERT",
            "alert_type": "WRONG_PARKING",
            "track_id": 602,
            "camera_id": "cam-2",
            "message": "Test wrong parking event",
            "snapshot_url": "/media/alerts/test.jpg",
        }, headers={"x-api-key": "dev-key"})
        assert alert_event.status_code == 201
        assert alert_event.json()["alert"]["alert_type"] == "WRONG_PARKING"
        print("  -> PASSED: Canonical AI payload, camera-scoped session enrichment, and alert mapping verified.", flush=True)

        print("Running Test 4: Plate Normalization & Stolen Vehicle Match...", flush=True)
        # Plate event for track 501 with watchlist match
        r_plate = await client.post("/api/v1/ai-events", json={
            "type": "plate",
            "trackId": 501,
            "plate": " rj 14-ab 1234 "
        }, headers={"x-api-key": "dev-key"})
        assert r_plate.status_code == 201
        d_plate = r_plate.json()
        assert d_plate["alert"] is not None
        assert d_plate["alert"]["alert_type"] == "STOLEN_VEHICLE"
        assert d_plate["alert"]["severity"] == "HIGH"
        assert d_plate["alert"]["plate_number"] == "RJ14AB1234"
        print("  -> PASSED: Stolen vehicle alert triggered immediately.", flush=True)

        print("Running Test 5: Vehicle Parked and Exit Duration...", flush=True)
        # Parked in B-01
        r_park = await client.post(
            "/api/v1/ai-events",
            json={"type": "parked", "trackId": 501, "slotId": "B-01"},
            headers={"x-api-key": "dev-key"},
        )
        assert r_park.status_code == 201
        assert r_park.json()["slot"]["status"] == "OCCUPIED"

        # Exit
        r_exit = await client.post(
            "/api/v1/ai-events",
            json={"type": "exit", "trackId": 501},
            headers={"x-api-key": "dev-key"},
        )
        assert r_exit.status_code == 201
        d_exit = r_exit.json()
        assert d_exit["session"]["status"] == "COMPLETED"

        # Slot freed
        slot_res = await client.get("/api/v1/slots/B-01")
        assert slot_res.json()["status"] == "AVAILABLE"
        print("  -> PASSED: Vehicle parking lifecycle & duration completed.", flush=True)

        print("Running Test 6: Watchlist CRUD and Constraints...", flush=True)
        r_w = await client.post("/api/v1/watchlist", json={"plate_number": "UP16XY1234", "reason": "SUSPICIOUS"})
        assert r_w.status_code == 201
        assert r_w.json()["plate_number"] == "UP16XY1234"

        # Duplicate constraint
        r_dup_w = await client.post("/api/v1/watchlist", json={"plate_number": "UP16XY1234", "reason": "DUP"})
        assert r_dup_w.status_code == 409

        # List with pagination
        r_w_list = await client.get("/api/v1/watchlist")
        assert r_w_list.status_code == 200
        assert "X-Total-Count" in r_w_list.headers
        print("  -> PASSED: Watchlist CRUD verified.", flush=True)

        print("Running Test 7: Sessions & Alerts Pagination and Filtering...", flush=True)
        r_sess = await client.get("/api/v1/sessions?plate=RJ14&status=completed&page=1&limit=10")
        assert r_sess.status_code == 200
        assert "X-Total-Count" in r_sess.headers

        r_alerts = await client.get("/api/v1/alerts?type=STOLEN_VEHICLE&acknowledged=false")
        assert r_alerts.status_code == 200
        assert "X-Total-Count" in r_alerts.headers
        alerts = r_alerts.json()
        assert len(alerts) >= 1
        alert_id = alerts[0]["alert_id"]

        # Ack alert
        r_ack = await client.patch(f"/api/v1/alerts/{alert_id}/ack")
        assert r_ack.status_code == 200
        assert r_ack.json()["is_acknowledged"] is True
        print("  -> PASSED: Pagination, filters, and alert ack verified.", flush=True)

        print("Running Test 8: Overstay Checker Logic...", flush=True)
        from datetime import timedelta
        db = SessionLocal()
        past_entry = datetime.now(timezone.utc) - timedelta(hours=5)
        overstay_sess = VehicleSession(
            session_id="test-overstay-session",
            track_id=999,
            plate_number="DL01OVERSTAY",
            vehicle_category="COMPACT_CAR",
            entry_time=past_entry,
            status="ACTIVE",
            overstay_alerted=False,
        )
        db.add(overstay_sess)
        db.commit()
        db.close()

        await check_active_sessions_for_overstay()

        db = SessionLocal()
        updated_s = db.query(VehicleSession).filter(VehicleSession.session_id == "test-overstay-session").first()
        assert updated_s.status == "OVERSTAY"
        assert updated_s.overstay_alerted is True
        alert_rec = db.query(Alert).filter(Alert.plate_number == "DL01OVERSTAY").first()
        assert alert_rec is not None
        assert alert_rec.alert_type == "OVERSTAY"
        db.close()
        print("  -> PASSED: Overstay alert triggered and session status updated.", flush=True)

        print("Running Test 9: Camera zone synchronization...", flush=True)
        db = SessionLocal()
        db.add(ParkingSlot(
            slot_id="KEEP-ME",
            camera_id="cam-1",
            zone="ZONE-X",
            allowed_category="COMPACT_CAR",
            polygon_coords=[[1, 1], [2, 1], [2, 2]],
        ))
        db.commit()
        slot_count_before_sync = db.query(ParkingSlot).count()
        slot_ids_before_sync = {slot.slot_id for slot in db.query(ParkingSlot.slot_id).all()}
        db.close()

        zone_file = backend_dir.parent / "ai-service" / "config" / "slots.json"
        configured_slot_ids = {
            slot["slotId"] for slot in json.loads(zone_file.read_text(encoding="utf-8"))["slots"]
        }
        expected_new_slots = len(configured_slot_ids - slot_ids_before_sync)
        sync_slots(zone_file, "cam-1")

        db = SessionLocal()
        try:
            assert db.query(ParkingSlot).count() == slot_count_before_sync + expected_new_slots
            assert db.query(ParkingSlot).filter(ParkingSlot.slot_id == "KEEP-ME").first().polygon_coords is None
            assert db.query(ParkingSlot).filter(ParkingSlot.slot_id == "B-01").first().polygon_coords is None
            assert db.query(ParkingSlot).filter(ParkingSlot.slot_id == "A-01").first().polygon_coords
            assert db.query(ParkingSlot).filter(ParkingSlot.slot_id == "A-04").first().polygon_coords
            assert db.query(ParkingSlot).filter(
                ParkingSlot.camera_id == "cam-1",
                ParkingSlot.polygon_coords.isnot(None),
                ParkingSlot.polygon_coords != JSON.NULL,
            ).count() == 5
        finally:
            db.close()
        print("  -> PASSED: Zone map updates without deleting slots or retaining stale polygons.", flush=True)

    print("\n==========================================", flush=True)
    print(" ALL BACKEND SERVICE CHECKS PASSED! ", flush=True)
    print("==========================================", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_async_tests())
    finally:
        engine.dispose()
        Path(test_db.name).unlink(missing_ok=True)
