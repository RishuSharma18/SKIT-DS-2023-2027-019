from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.database import get_db
from app.models.parking_slot import ParkingSlot

router = APIRouter(prefix="/cameras", tags=["Camera Zones"])


@router.get("/{camera_id}/zones", dependencies=[Depends(verify_api_key)])
def get_camera_zones(camera_id: str, db: Session = Depends(get_db)):
    slots = (
        db.query(ParkingSlot)
        .filter(ParkingSlot.camera_id == camera_id)
        .order_by(ParkingSlot.zone.asc(), ParkingSlot.slot_id.asc())
        .all()
    )
    return {
        "camera_id": camera_id,
        "slots": [
            {
                "slot_id": slot.slot_id,
                "vehicle_category": slot.allowed_category,
                "polygon": slot.polygon_coords,
            }
            for slot in slots
            if isinstance(slot.polygon_coords, list) and len(slot.polygon_coords) >= 3
        ],
        "no_parking_zones": [],
        "tripwires": [],
    }
