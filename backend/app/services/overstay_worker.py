import asyncio
import logging
import uuid
from datetime import datetime, timezone
from app.config import settings
from app.database import SessionLocal
from app.models.vehicle_session import VehicleSession
from app.models.alert import Alert
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

async def run_overstay_checker(stop_event: asyncio.Event = None):
    """
    Background worker running every 60 seconds checking ACTIVE sessions
    exceeding MAX_ALLOWED_DURATION_MINUTES. Triggers OVERSTAY alert once per session.
    """
    logger.info(
        f"Starting Overstay Worker (Interval: {settings.OVERSTAY_CHECK_INTERVAL_SECONDS}s, Threshold: {settings.MAX_ALLOWED_DURATION_MINUTES}m)"
    )
    while True:
        if stop_event and stop_event.is_set():
            break

        try:
            await check_active_sessions_for_overstay()
        except asyncio.CancelledError:
            logger.info("Overstay worker cancelled.")
            break
        except Exception as exc:
            logger.error(f"Error in overstay worker: {exc}")

        try:
            if stop_event:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=settings.OVERSTAY_CHECK_INTERVAL_SECONDS)
                    break
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(settings.OVERSTAY_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break

async def check_active_sessions_for_overstay():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        active_sessions = (
            db.query(VehicleSession)
            .filter(
                VehicleSession.status == "ACTIVE",
                VehicleSession.overstay_alerted == False
            )
            .all()
        )

        for session in active_sessions:
            entry_tz = session.entry_time
            if entry_tz.tzinfo is None:
                entry_tz = entry_tz.replace(tzinfo=timezone.utc)

            elapsed_minutes = (now - entry_tz).total_seconds() / 60.0
            if elapsed_minutes >= settings.MAX_ALLOWED_DURATION_MINUTES:
                session.overstay_alerted = True
                session.status = "OVERSTAY"
                session.duration_minutes = round(elapsed_minutes, 2)

                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="OVERSTAY",
                    severity="MEDIUM",
                    plate_number=session.plate_number,
                    slot_id=session.actual_slot_id or session.assigned_slot_id,
                    camera_id=session.camera_id or "cam-1",
                    message=(
                        f"Overstay detected: Vehicle {session.plate_number or f'Track #{session.track_id}'} "
                        f"exceeded maximum allowed duration of {settings.MAX_ALLOWED_DURATION_MINUTES} minutes "
                        f"(parked for {int(elapsed_minutes)} mins)."
                    ),
                    is_acknowledged=False,
                    created_at=now,
                )
                db.add(alert)
                db.commit()
                db.refresh(session)
                db.refresh(alert)

                logger.warning(
                    f"OVERSTAY ALERT generated for track {session.track_id} (Plate: {session.plate_number})"
                )
                await ws_manager.broadcast_alert(alert.to_dict())
                await ws_manager.broadcast_session_update(session.to_dict())

    finally:
        db.close()
