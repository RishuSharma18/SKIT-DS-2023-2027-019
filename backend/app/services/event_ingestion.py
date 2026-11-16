import uuid
from datetime import datetime, timezone
import logging
from typing import Tuple, Optional, Any
from sqlalchemy.orm import Session
from app.models.parking_slot import ParkingSlot
from app.models.vehicle_session import VehicleSession
from app.models.watchlist import Watchlist
from app.models.alert import Alert
from app.schemas.event import AIEventPayload
from app.services.redis_service import redis_service
from app.services.websocket_manager import ws_manager
from app.services.allocation_engine import allocate_nearest_slot, normalize_category
from app.services.snapshot_service import save_base64_snapshot

logger = logging.getLogger(__name__)

def normalize_plate(plate: Optional[str]) -> Optional[str]:
    if not plate:
        return None
    return plate.strip().upper().replace(" ", "").replace("-", "")

async def check_watchlist_match(
    db: Session,
    plate_number: str,
    camera_id: str = "cam-1",
    slot_id: Optional[str] = None,
    snapshot_url: Optional[str] = None
) -> Optional[Alert]:
    if not plate_number:
        return None

    normalized = normalize_plate(plate_number)
    is_stolen = redis_service.is_plate_in_watchlist(normalized)

    # If not in cache, fallback check in DB
    reason = "STOLEN"
    if not is_stolen:
        hit = (
            db.query(Watchlist)
            .filter(Watchlist.plate_number == normalized, Watchlist.is_active == True)
            .first()
        )
        if hit:
            is_stolen = True
            reason = hit.reason
            redis_service.add_watchlist_plate(normalized)

    if is_stolen:
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            alert_type="STOLEN_VEHICLE",
            severity="HIGH",
            plate_number=normalized,
            slot_id=slot_id,
            camera_id=camera_id,
            snapshot_url=snapshot_url,
            message=f"CRITICAL: Stolen vehicle detected on camera {camera_id}: {normalized} (Reason: {reason})",
            is_acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        await ws_manager.broadcast_alert(alert.to_dict())
        logger.warning(f"HIGH ALERT - STOLEN_VEHICLE: {normalized}")
        return alert

    return None

async def process_ai_event(db: Session, payload: AIEventPayload) -> dict[str, Any]:
    event_type = payload.type.strip().lower()
    track_id = payload.track_id
    raw_plate = payload.plate_number
    normalized_plate = normalize_plate(raw_plate)
    vehicle_cat = payload.vehicle_category or "COMPACT_CAR"
    slot_id = payload.slot_id
    camera_id = payload.camera_id or "cam-1"
    message = payload.message

    snapshot_url = None
    if payload.snapshot:
        snapshot_url = save_base64_snapshot(payload.snapshot)

    result: dict[str, Any] = {
        "success": True,
        "event_type": event_type,
        "message": f"Processed {event_type} event",
    }

    # 1. ENTRY EVENT
    if event_type == "entry":
        # Idempotency check: prevent duplicate entry records for same track_id
        if track_id is not None:
            idempotency_key = f"event:entry:{track_id}"
            is_new = redis_service.check_and_set_idempotency(idempotency_key, ttl_seconds=10)

            # Check if active session already exists in DB
            existing_session = (
                db.query(VehicleSession)
                .filter(VehicleSession.track_id == track_id, VehicleSession.status == "ACTIVE")
                .first()
            )
            if existing_session or not is_new:
                logger.info(f"Idempotency triggered for duplicate entry event on track {track_id}")
                result["message"] = "Duplicate entry frame ignored (idempotent)"
                result["session"] = existing_session.to_dict() if existing_session else None
                return result

        # Smart slot allocation on entry
        allocated_slot, alloc_msg = allocate_nearest_slot(
            db, vehicle_cat, track_id=track_id, reserve=True
        )

        session = VehicleSession(
            session_id=str(uuid.uuid4()),
            track_id=track_id or 0,
            plate_number=normalized_plate,
            vehicle_category=normalize_category(vehicle_cat),
            assigned_slot_id=allocated_slot.slot_id if allocated_slot else None,
            camera_id=camera_id,
            status="ACTIVE",
            entry_time=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        result["session"] = session.to_dict()
        if allocated_slot:
            result["allocation"] = {
                "recommended_slot_id": allocated_slot.slot_id,
                "zone": allocated_slot.zone,
                "allowed_category": allocated_slot.allowed_category,
                "status": allocated_slot.status,
            }

        # Watchlist check if plate was provided on entry
        if normalized_plate:
            alert = await check_watchlist_match(
                db, normalized_plate, camera_id, session.assigned_slot_id, snapshot_url
            )
            if alert:
                result["alert"] = alert.to_dict()

        await ws_manager.broadcast_session_new(session.to_dict())
        slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
        await ws_manager.broadcast_slot_update(slots)
        return result

    # 2. PLATE RECOGNITION EVENT
    elif event_type == "plate":
        session = None
        if track_id is not None:
            session = (
                db.query(VehicleSession)
                .filter(VehicleSession.track_id == track_id, VehicleSession.status == "ACTIVE")
                .order_by(VehicleSession.created_at.desc())
                .first()
            )
            if session:
                session.plate_number = normalized_plate
                db.commit()
                db.refresh(session)
                result["session"] = session.to_dict()
                await ws_manager.broadcast_session_update(session.to_dict())

        # Check stolen vehicle watchlist
        alert = await check_watchlist_match(
            db,
            normalized_plate or "",
            camera_id,
            session.actual_slot_id if session else slot_id,
            snapshot_url
        )
        if alert:
            result["alert"] = alert.to_dict()
        return result

    # 3. PARKED EVENT
    elif event_type == "parked":
        session = None
        if track_id is not None:
            session = (
                db.query(VehicleSession)
                .filter(VehicleSession.track_id == track_id, VehicleSession.status == "ACTIVE")
                .first()
            )
            if session and slot_id:
                session.actual_slot_id = slot_id
                db.commit()
                db.refresh(session)
                result["session"] = session.to_dict()
                await ws_manager.broadcast_session_update(session.to_dict())

        if slot_id:
            slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
            if slot:
                slot.status = "OCCUPIED"
                slot.current_track_id = track_id
                db.commit()
                db.refresh(slot)
                result["slot"] = slot.to_dict()

        slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
        await ws_manager.broadcast_slot_update(slots)
        return result

    # 4. EXIT EVENT
    elif event_type == "exit":
        session = None
        if track_id is not None:
            session = (
                db.query(VehicleSession)
                .filter(VehicleSession.track_id == track_id, VehicleSession.status == "ACTIVE")
                .first()
            )
            if session:
                exit_now = datetime.now(timezone.utc)
                session.exit_time = exit_now
                entry_tz = session.entry_time
                if entry_tz.tzinfo is None:
                    entry_tz = entry_tz.replace(tzinfo=timezone.utc)
                diff_minutes = (exit_now - entry_tz).total_seconds() / 60.0
                session.duration_minutes = max(0.0, round(diff_minutes, 2))
                session.status = "COMPLETED"
                db.commit()
                db.refresh(session)
                result["session"] = session.to_dict()
                await ws_manager.broadcast_session_update(session.to_dict())

                # Free occupied slot
                occupied_slot_id = session.actual_slot_id or session.assigned_slot_id
                if occupied_slot_id:
                    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == occupied_slot_id).first()
                    if slot:
                        slot.status = "AVAILABLE"
                        slot.current_track_id = None
                        db.commit()

        slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
        await ws_manager.broadcast_slot_update(slots)
        return result

    # 5. WRONG PARKING EVENT
    elif event_type == "wrong_parking":
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            alert_type="WRONG_PARKING",
            severity="MEDIUM",
            plate_number=normalized_plate,
            slot_id=slot_id,
            camera_id=camera_id,
            snapshot_url=snapshot_url,
            message=message or f"Vehicle stationary outside assigned slot polygon (track: {track_id})",
            is_acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        if slot_id:
            slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
            if slot:
                slot.status = "VIOLATION"
        db.commit()
        db.refresh(alert)
        result["alert"] = alert.to_dict()
        await ws_manager.broadcast_alert(alert.to_dict())
        return result

    # 6. CRASH / ACCIDENT EVENT
    elif event_type in ["crash", "accident"]:
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            alert_type="ACCIDENT",
            severity="HIGH",
            plate_number=normalized_plate,
            slot_id=slot_id,
            camera_id=camera_id,
            snapshot_url=snapshot_url,
            message=message or f"Collision / Sudden deceleration detected on camera {camera_id}",
            is_acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        result["alert"] = alert.to_dict()
        await ws_manager.broadcast_alert(alert.to_dict())
        return result

    # 7. STOLEN VEHICLE DIRECT EVENT
    elif event_type == "stolen_vehicle":
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            alert_type="STOLEN_VEHICLE",
            severity="HIGH",
            plate_number=normalized_plate,
            slot_id=slot_id,
            camera_id=camera_id,
            snapshot_url=snapshot_url,
            message=message or f"Watchlist hit: Stolen vehicle identified ({normalized_plate})",
            is_acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        result["alert"] = alert.to_dict()
        await ws_manager.broadcast_alert(alert.to_dict())
        return result

    else:
        result["message"] = f"Unknown event type: {event_type}"
        return result
