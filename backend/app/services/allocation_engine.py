import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.parking_slot import ParkingSlot

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "bike": "TWO_WHEELER",
    "motorcycle": "TWO_WHEELER",
    "two_wheeler": "TWO_WHEELER",
    "car": "COMPACT_CAR",
    "sedan": "COMPACT_CAR",
    "compact_car": "COMPACT_CAR",
    "suv": "SUV_SEDAN",
    "suv_sedan": "SUV_SEDAN",
    "truck": "HEAVY_VEHICLE",
    "bus": "HEAVY_VEHICLE",
    "heavy_vehicle": "HEAVY_VEHICLE",
}

FALLBACK_HIERARCHY = {
    "TWO_WHEELER": ["TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN"],
    "COMPACT_CAR": ["COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"],
    "SUV_SEDAN": ["SUV_SEDAN", "HEAVY_VEHICLE"],
    "HEAVY_VEHICLE": ["HEAVY_VEHICLE"],
}

def normalize_category(category_raw: str) -> str:
    cleaned = category_raw.strip().lower() if category_raw else "compact_car"
    return CATEGORY_MAP.get(cleaned, category_raw.upper())

def allocate_nearest_slot(
    db: Session,
    vehicle_category: str,
    track_id: Optional[int] = None,
    reserve: bool = True
) -> Tuple[Optional[ParkingSlot], str]:
    """
    Finds nearest AVAILABLE slot matching exact category,
    falling back to next larger category if exact is full.
    If reserve=True, marks slot as RESERVED.
    """
    normalized_cat = normalize_category(vehicle_category)
    candidate_categories = FALLBACK_HIERARCHY.get(normalized_cat, [normalized_cat])

    selected_slot: Optional[ParkingSlot] = None

    for cat in candidate_categories:
        slot = (
            db.query(ParkingSlot)
            .filter(
                ParkingSlot.status == "AVAILABLE",
                ParkingSlot.allowed_category == cat
            )
            .order_by(ParkingSlot.zone.asc(), ParkingSlot.slot_id.asc())
            .first()
        )
        if slot:
            selected_slot = slot
            break

    if not selected_slot:
        return None, f"No available parking slots found for category {normalized_cat} (or fallbacks)."

    if reserve:
        selected_slot.status = "RESERVED"
        if track_id is not None:
            selected_slot.current_track_id = track_id
        db.commit()
        db.refresh(selected_slot)
        logger.info(
            f"Allocated slot {selected_slot.slot_id} in {selected_slot.zone} (category: {selected_slot.allowed_category}) for track {track_id}"
        )

    return selected_slot, f"Slot {selected_slot.slot_id} ({selected_slot.zone}) allocated successfully."
