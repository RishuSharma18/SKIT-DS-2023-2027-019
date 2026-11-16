import logging
import math
from typing import Optional, Tuple
from sqlalchemy import String, cast
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
    reserve: bool = True,
    camera_id: Optional[str] = None,
    reference_point: Optional[tuple[float, float]] = None,
) -> Tuple[Optional[ParkingSlot], str]:
    """
    Finds the nearest AVAILABLE slot matching exact category when a camera-frame
    reference point is supplied, falling back to the next larger category.
    Without a point, selection is deterministic by zone and slot ID.
    If reserve=True, marks slot as RESERVED.
    """
    normalized_cat = normalize_category(vehicle_category)
    candidate_categories = FALLBACK_HIERARCHY.get(normalized_cat, [normalized_cat])

    selected_slot: Optional[ParkingSlot] = None

    for cat in candidate_categories:
        query = db.query(ParkingSlot).filter(
            ParkingSlot.status == "AVAILABLE",
            ParkingSlot.allowed_category == cat,
            ParkingSlot.polygon_coords.isnot(None),
            cast(ParkingSlot.polygon_coords, String) != "null",
        )
        if camera_id:
            query = query.filter(ParkingSlot.camera_id == camera_id)
        candidates = query.order_by(ParkingSlot.zone.asc(), ParkingSlot.slot_id.asc()).all()
        if reference_point:
            candidates = sorted(
                candidates,
                key=lambda candidate: (
                    _distance_to_slot(candidate, reference_point),
                    candidate.zone,
                    candidate.slot_id,
                ),
            )
        slot = candidates[0] if candidates else None
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


def _distance_to_slot(slot: ParkingSlot, point: tuple[float, float]) -> float:
    polygon = slot.polygon_coords
    if not isinstance(polygon, list) or len(polygon) < 3:
        return math.inf
    try:
        vertices = [(float(vertex[0]), float(vertex[1])) for vertex in polygon]
        if any(not math.isfinite(value) for vertex in vertices for value in vertex):
            return math.inf
    except (TypeError, ValueError, IndexError):
        return math.inf
    cross_terms = [
        x * vertices[(index + 1) % len(vertices)][1]
        - vertices[(index + 1) % len(vertices)][0] * y
        for index, (x, y) in enumerate(vertices)
    ]
    twice_area = sum(cross_terms)
    if math.isclose(twice_area, 0.0):
        return math.inf
    center_x = sum(
        (vertices[index][0] + vertices[(index + 1) % len(vertices)][0]) * cross
        for index, cross in enumerate(cross_terms)
    ) / (3 * twice_area)
    center_y = sum(
        (vertices[index][1] + vertices[(index + 1) % len(vertices)][1]) * cross
        for index, cross in enumerate(cross_terms)
    ) / (3 * twice_area)
    return math.hypot(center_x - point[0], center_y - point[1])
