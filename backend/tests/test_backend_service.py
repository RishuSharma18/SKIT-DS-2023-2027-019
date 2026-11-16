import os
import sys
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# Use SQLite for fast in-memory / local unit tests
test_db_path = backend_path / "test_cctv.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, init_db
from app.models.parking_slot import ParkingSlot
from app.models.vehicle_session import VehicleSession
from app.models.watchlist import Watchlist
from app.models.alert import Alert
from app.services.redis_service import redis_service
from app.services.overstay_worker import check_active_sessions_for_overstay

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()
    try:
        # Clear test records
        db.query(Alert).delete()
        db.query(VehicleSession).delete()
        db.query(ParkingSlot).delete()
        db.query(Watchlist).delete()

        # Add initial slots
        db.add_all([
            ParkingSlot(slot_id="A-01", zone="ZONE-A", allowed_category="TWO_WHEELER", status="AVAILABLE"),
            ParkingSlot(slot_id="A-02", zone="ZONE-A", allowed_category="COMPACT_CAR", status="AVAILABLE"),
            ParkingSlot(slot_id="B-01", zone="ZONE-B", allowed_category="SUV_SEDAN", status="AVAILABLE"),
            ParkingSlot(slot_id="C-01", zone="ZONE-C", allowed_category="HEAVY_VEHICLE", status="AVAILABLE"),
        ])

        # Add initial watchlist
        db.add(Watchlist(plate_number="RJ14AB1234", reason="STOLEN", is_active=True))
        db.commit()

        redis_service.populate_watchlist_cache({"RJ14AB1234"})
    finally:
        db.close()

def test_openapi_docs_generated():
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "paths" in schema
    assert "/api/v1/ai-events" in schema["paths"]
    assert "/api/v1/slots/allocate" in schema["paths"]
    assert "/api/v1/watchlist" in schema["paths"]
    assert "/api/v1/sessions" in schema["paths"]
    assert "/api/v1/alerts" in schema["paths"]

def test_smart_slot_allocation_exact_and_fallback():
    # 1. Exact match for TWO_WHEELER
    res1 = client.post("/api/v1/slots/allocate", json={"vehicle_category": "TWO_WHEELER"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["recommended_slot_id"] == "A-01"
    assert data1["zone"] == "ZONE-A"
    assert data1["status"] == "RESERVED"

    # 2. When TWO_WHEELER is reserved/full, fallback to next larger category (COMPACT_CAR)
    res2 = client.post("/api/v1/slots/allocate", json={"vehicle_category": "TWO_WHEELER"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["recommended_slot_id"] == "A-02"
    assert data2["zone"] == "ZONE-A"

def test_ai_events_entry_and_idempotency():
    payload = {
        "type": "entry",
        "trackId": 501,
        "vehicleType": "COMPACT_CAR",
        "cameraId": "cam-1"
    }
    # First entry
    res1 = client.post("/api/v1/ai-events", json=payload, headers={"x-api-key": "dev-key"})
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["session"]["track_id"] == 501
    assert data1["allocation"]["recommended_slot_id"] == "A-02"

    # Duplicate entry frame (idempotency check)
    res2 = client.post("/api/v1/ai-events", json=payload, headers={"x-api-key": "dev-key"})
    assert res2.status_code == 201
    data2 = res2.json()
    assert "Duplicate entry frame ignored" in data2["message"]

    # Verify only 1 session was created in DB
    db = SessionLocal()
    sessions = db.query(VehicleSession).filter(VehicleSession.track_id == 501).all()
    assert len(sessions) == 1
    db.close()

def test_stolen_vehicle_matching_and_alert():
    # 1. Create entry for track 701
    client.post("/api/v1/ai-events", json={
        "type": "entry",
        "trackId": 701,
        "vehicleType": "car"
    })

    # 2. Plate recognized matching watchlist (with spaces and lowercase to test normalization)
    res = client.post("/api/v1/ai-events", json={
        "type": "plate",
        "trackId": 701,
        "plate": "rj 14-ab 1234"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["alert"] is not None
    assert data["alert"]["alert_type"] == "STOLEN_VEHICLE"
    assert data["alert"]["severity"] == "HIGH"
    assert data["alert"]["plate_number"] == "RJ14AB1234"

def test_vehicle_lifecycle_parked_and_exit():
    # Entry
    client.post("/api/v1/ai-events", json={"type": "entry", "trackId": 801, "vehicleType": "COMPACT_CAR"})

    # Parked in A-02
    res_park = client.post("/api/v1/ai-events", json={"type": "parked", "trackId": 801, "slotId": "A-02"})
    assert res_park.status_code == 201
    assert res_park.json()["slot"]["status"] == "OCCUPIED"

    # Exit
    res_exit = client.post("/api/v1/ai-events", json={"type": "exit", "trackId": 801})
    assert res_exit.status_code == 201
    session = res_exit.json()["session"]
    assert session["status"] == "COMPLETED"
    assert session["exit_time"] is not None

    # Check slot is freed
    slot_res = client.get("/api/v1/slots/A-02")
    assert slot_res.json()["status"] == "AVAILABLE"

def test_watchlist_crud_and_conflict():
    # Create
    res = client.post("/api/v1/watchlist", json={"plate_number": "UP16XY1234", "reason": "SUSPICIOUS"})
    assert res.status_code == 201
    assert res.json()["plate_number"] == "UP16XY1234"

    # Conflict on duplicate
    res_dup = client.post("/api/v1/watchlist", json={"plate_number": "UP16XY1234", "reason": "DUP"})
    assert res_dup.status_code == 409

    # List
    res_list = client.get("/api/v1/watchlist")
    assert res_list.status_code == 200
    assert "X-Total-Count" in res_list.headers

def test_sessions_and_alerts_filtering_pagination():
    # Insert dummy sessions
    db = SessionLocal()
    db.add(VehicleSession(track_id=1, plate_number="RJ14CA0001", status="ACTIVE", vehicle_category="COMPACT_CAR"))
    db.add(VehicleSession(track_id=2, plate_number="RJ14CA0002", status="COMPLETED", vehicle_category="COMPACT_CAR"))
    db.add(Alert(alert_id="a-1", alert_type="ACCIDENT", severity="HIGH", is_acknowledged=False))
    db.commit()
    db.close()

    # Filter sessions
    res = client.get("/api/v1/sessions?plate=RJ14&status=completed&page=1&limit=10")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.headers["X-Total-Count"] == "1"

    # Filter alerts
    res_alerts = client.get("/api/v1/alerts?type=ACCIDENT&acknowledged=false")
    assert res_alerts.status_code == 200
    assert len(res_alerts.json()) == 1
    assert res_alerts.headers["X-Total-Count"] == "1"

    # Ack alert
    res_ack = client.patch("/api/v1/alerts/a-1/ack")
    assert res_ack.status_code == 200
    assert res_ack.json()["is_acknowledged"] is True

def test_overstay_checker():
    from datetime import datetime, timedelta, timezone
    db = SessionLocal()
    past_entry = datetime.now(timezone.utc) - timedelta(hours=5)
    session = VehicleSession(
        session_id="overstay-session-1",
        track_id=999,
        plate_number="DL01OVERSTAY",
        vehicle_category="COMPACT_CAR",
        entry_time=past_entry,
        status="ACTIVE",
        overstay_alerted=False,
    )
    db.add(session)
    db.commit()
    db.close()

    # Run overstay checker synchronously
    asyncio.run(check_active_sessions_for_overstay())

    # Verify session marked OVERSTAY and alert created
    db = SessionLocal()
    updated_session = db.query(VehicleSession).filter(VehicleSession.session_id == "overstay-session-1").first()
    assert updated_session.status == "OVERSTAY"
    assert updated_session.overstay_alerted is True

    alert = db.query(Alert).filter(Alert.plate_number == "DL01OVERSTAY").first()
    assert alert is not None
    assert alert.alert_type == "OVERSTAY"
    db.close()
