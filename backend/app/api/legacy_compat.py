from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.parking_slot import ParkingSlot
from app.models.vehicle_session import VehicleSession
from app.models.watchlist import Watchlist
from app.models.alert import Alert
from app.schemas.event import AIEventPayload
from app.services.allocation_engine import allocate_nearest_slot
from app.services.event_ingestion import process_ai_event

legacy_router = APIRouter(prefix="/api", tags=["Legacy Frontend Compatibility"])

@legacy_router.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@legacy_router.get("/stats")
def stats(db: Session = Depends(get_db)):
    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_slots = db.query(ParkingSlot).count()
    free_slots = db.query(ParkingSlot).filter(ParkingSlot.status == "AVAILABLE").count()
    occupied = db.query(ParkingSlot).filter(ParkingSlot.status == "OCCUPIED").count()
    active_vehicles = db.query(VehicleSession).filter(VehicleSession.status == "ACTIVE").count()
    today_entries = db.query(VehicleSession).filter(VehicleSession.entry_time >= start_of_today).count()
    open_alerts = db.query(Alert).filter(Alert.is_acknowledged == False).count()

    return {
        "totalSlots": total_slots,
        "freeSlots": free_slots,
        "occupied": occupied,
        "occupiedSlots": occupied,
        "activeVehicles": active_vehicles,
        "todayEntries": today_entries,
        "openAlerts": open_alerts,
    }

@legacy_router.get("/analytics/hourly")
def hourly_analytics(
    date: Optional[str] = Query(None),
    nonzero: Optional[bool] = Query(False),
    db: Session = Depends(get_db)
):
    sessions = db.query(VehicleSession).all()
    hourly = [{"hour": i, "entries": 0} for i in range(24)]
    for s in sessions:
        if s.entry_time:
            h = s.entry_time.hour
            if 0 <= h < 24:
                hourly[h]["entries"] += 1

    if nonzero:
        return [h for h in hourly if h["entries"] > 0]
    return hourly

@legacy_router.get("/slots")
def get_slots_compat(db: Session = Depends(get_db)):
    slots = db.query(ParkingSlot).order_by(ParkingSlot.zone.asc(), ParkingSlot.slot_id.asc()).all()
    return [
        {
            "_id": s.slot_id,
            "slotId": s.slot_id,
            "zone": s.zone,
            "type": "car" if "CAR" in s.allowed_category else "bike" if "TWO" in s.allowed_category else "suv",
            "status": "free" if s.status == "AVAILABLE" else "occupied" if s.status == "OCCUPIED" else "reserved",
            "polygonCoords": s.polygon_coords,
        }
        for s in slots
    ]

@legacy_router.get("/slots/recommend")
def recommend_slot_compat(
    type: str = Query("car"),
    vehicleType: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    cat = vehicleType or type
    slot, _ = allocate_nearest_slot(db, cat, reserve=False)
    if not slot:
        return {"slot": None}
    return {
        "slot": {
            "_id": slot.slot_id,
            "slotId": slot.slot_id,
            "zone": slot.zone,
            "type": slot.allowed_category,
            "status": slot.status,
        }
    }

@legacy_router.get("/sessions")
def get_sessions_compat(
    response: Response,
    plate: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(VehicleSession)
    if plate:
        cleaned = plate.strip().upper().replace(" ", "").replace("-", "")
        query = query.filter(VehicleSession.plate_number.contains(cleaned))
    if status:
        query = query.filter(VehicleSession.status == status.upper())

    total = query.count()
    items = query.order_by(VehicleSession.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

    return [
        {
            "_id": s.session_id,
            "trackId": s.track_id,
            "plate": s.plate_number,
            "vehicleType": s.vehicle_category,
            "slotId": s.actual_slot_id or s.assigned_slot_id,
            "entryTime": s.entry_time.isoformat() if s.entry_time else None,
            "exitTime": s.exit_time.isoformat() if s.exit_time else None,
            "durationSec": int(s.duration_minutes * 60) if s.duration_minutes else 0,
            "status": "active" if s.status == "ACTIVE" else "closed",
        }
        for s in items
    ]

@legacy_router.get("/alerts")
def get_alerts_compat(
    response: Response,
    type: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if type and type.lower() != "all":
        query = query.filter(Alert.alert_type == type.upper())
    if acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == acknowledged)

    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

    return [
        {
            "_id": a.alert_id,
            "type": a.alert_type.lower(),
            "severity": a.severity.lower(),
            "plate": a.plate_number,
            "slotId": a.slot_id,
            "cameraId": a.camera_id,
            "snapshot": a.snapshot_url,
            "message": a.message,
            "acknowledged": a.is_acknowledged,
            "createdAt": a.created_at.isoformat() if a.created_at else None,
        }
        for s, a in enumerate(items)
    ]

@legacy_router.patch("/alerts/{id}/ack")
def ack_alert_compat(id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == id).first()
    if alert:
        alert.is_acknowledged = True
        db.commit()
        db.refresh(alert)
        return {
            "_id": alert.alert_id,
            "acknowledged": True,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
    return {"_id": id, "acknowledged": True}

@legacy_router.get("/watchlist")
def get_watchlist_compat(db: Session = Depends(get_db)):
    items = db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()
    return [
        {
            "_id": str(w.id),
            "plate": w.plate_number,
            "reason": w.reason,
            "active": w.is_active,
            "createdAt": w.created_at.isoformat() if w.created_at else None,
        }
        for w in items
    ]

@legacy_router.post("/watchlist", status_code=status.HTTP_201_CREATED)
def add_watchlist_compat(entry: dict[str, Any], db: Session = Depends(get_db)):
    plate = entry.get("plate") or entry.get("plate_number")
    reason = entry.get("reason", "STOLEN")
    normalized = plate.strip().upper().replace(" ", "").replace("-", "") if plate else "UNKNOWN"
    db_entry = Watchlist(plate_number=normalized, reason=reason, is_active=True)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return {"_id": str(db_entry.id), "plate": db_entry.plate_number, "reason": db_entry.reason, "active": True}

@legacy_router.delete("/watchlist/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_compat(id: str, db: Session = Depends(get_db)):
    try:
        int_id = int(id)
        entry = db.query(Watchlist).filter(Watchlist.id == int_id).first()
        if entry:
            db.delete(entry)
            db.commit()
    except Exception:
        pass
    return None

@legacy_router.post("/events", status_code=status.HTTP_201_CREATED)
async def post_event_compat(payload: AIEventPayload, db: Session = Depends(get_db)):
    return await process_ai_event(db, payload)
