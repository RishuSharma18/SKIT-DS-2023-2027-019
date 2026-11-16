import sys
import os
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
settings.ENABLE_OVERSTAY_WORKER = False

import httpx
from app.main import app
from app.database import SessionLocal, init_db
from app.models.parking_slot import ParkingSlot
from app.models.vehicle_session import VehicleSession
from app.models.watchlist import Watchlist
from app.models.alert import Alert
from app.services.redis_service import redis_service
from app.services.overstay_worker import check_active_sessions_for_overstay

def setup_data():
    init_db()
    db = SessionLocal()
    try:
        db.query(Alert).delete()
        db.query(VehicleSession).delete()
        db.query(ParkingSlot).delete()
        db.query(Watchlist).delete()

        db.add_all([
            ParkingSlot(slot_id="A-01", zone="ZONE-A", allowed_category="TWO_WHEELER", status="AVAILABLE"),
            ParkingSlot(slot_id="A-02", zone="ZONE-A", allowed_category="COMPACT_CAR", status="AVAILABLE"),
            ParkingSlot(slot_id="B-01", zone="ZONE-B", allowed_category="SUV_SEDAN", status="AVAILABLE"),
            ParkingSlot(slot_id="C-01", zone="ZONE-C", allowed_category="HEAVY_VEHICLE", status="AVAILABLE"),
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
        print("  -> PASSED: OpenAPI schema validated.", flush=True)

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

        print("Running Test 4: Plate Normalization & Stolen Vehicle Match...", flush=True)
        # Plate event for track 501 with watchlist match
        r_plate = await client.post("/api/v1/ai-events", json={
            "type": "plate",
            "trackId": 501,
            "plate": " rj 14-ab 1234 "
        })
        assert r_plate.status_code == 201
        d_plate = r_plate.json()
        assert d_plate["alert"] is not None
        assert d_plate["alert"]["alert_type"] == "STOLEN_VEHICLE"
        assert d_plate["alert"]["severity"] == "HIGH"
        assert d_plate["alert"]["plate_number"] == "RJ14AB1234"
        print("  -> PASSED: Stolen vehicle alert triggered immediately.", flush=True)

        print("Running Test 5: Vehicle Parked and Exit Duration...", flush=True)
        # Parked in B-01
        r_park = await client.post("/api/v1/ai-events", json={"type": "parked", "trackId": 501, "slotId": "B-01"})
        assert r_park.status_code == 201
        assert r_park.json()["slot"]["status"] == "OCCUPIED"

        # Exit
        r_exit = await client.post("/api/v1/ai-events", json={"type": "exit", "trackId": 501})
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
        from datetime import datetime, timedelta, timezone
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

    print("\n==========================================", flush=True)
    print(" ALL 8 BACKEND SERVICE TESTS PASSED 100%! ", flush=True)
    print("==========================================", flush=True)

if __name__ == "__main__":
    asyncio.run(run_async_tests())
