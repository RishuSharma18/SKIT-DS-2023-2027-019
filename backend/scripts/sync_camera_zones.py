import argparse
import json
import math
import sys
from pathlib import Path
from sqlalchemy import null

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, init_db
from app.models.parking_slot import ParkingSlot

CATEGORY_MAP = {
    "bike": "TWO_WHEELER",
    "two_wheeler": "TWO_WHEELER",
    "car": "COMPACT_CAR",
    "compact_car": "COMPACT_CAR",
    "sedan": "SUV_SEDAN",
    "suv": "SUV_SEDAN",
    "suv_sedan": "SUV_SEDAN",
    "truck": "HEAVY_VEHICLE",
    "bus": "HEAVY_VEHICLE",
    "heavy_vehicle": "HEAVY_VEHICLE",
}


def load_slots(path: Path):
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict) or not isinstance(data.get("slots"), list):
        raise ValueError(f"{path} must contain a 'slots' array.")

    slots = []
    for index, slot in enumerate(data["slots"]):
        if not isinstance(slot, dict):
            raise ValueError(f"Slot entry {index} must be an object.")
        slot_id = slot.get("slot_id") or slot.get("slotId")
        polygon = slot.get("polygon")
        raw_category = slot.get("type", slot.get("vehicle_category", "car"))
        category = CATEGORY_MAP.get(str(raw_category).lower())
        valid_polygon = (
            isinstance(polygon, list)
            and len(polygon) >= 3
            and all(
                isinstance(point, list)
                and len(point) == 2
                and all(
                    isinstance(value, (int, float)) and math.isfinite(value)
                    for value in point
                )
                for point in polygon
            )
        )
        if not slot_id or not valid_polygon or not category:
            raise ValueError(f"Slot entry {index} needs a slot ID, valid polygon, and supported type.")
        slots.append((str(slot_id), polygon, category))
    return slots


def sync_slots(path: Path, camera_id: str):
    slots = load_slots(path)
    init_db()
    db = SessionLocal()
    try:
        configured_ids = {slot_id for slot_id, _, _ in slots}
        stale_slots = db.query(ParkingSlot).filter(ParkingSlot.camera_id == camera_id)
        if configured_ids:
            stale_slots = stale_slots.filter(ParkingSlot.slot_id.notin_(configured_ids))
        stale_slots.update(
            {ParkingSlot.polygon_coords: null()},
            synchronize_session=False,
        )

        for slot_id, polygon, category in slots:
            slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
            if slot is None:
                slot = ParkingSlot(
                    slot_id=slot_id,
                    zone=slot_id.split("-", 1)[0],
                    allowed_category=category,
                    status="AVAILABLE",
                    camera_id=camera_id,
                )
                db.add(slot)
            slot.camera_id = camera_id
            slot.allowed_category = category
            slot.polygon_coords = polygon
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"Synced {len(slots)} camera-zone slots for {camera_id} from {path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upsert camera slot polygons from an AI-service zone file.")
    parser.add_argument(
        "--file",
        type=Path,
        default=backend_dir.parent / "ai-service" / "config" / "slots.json",
    )
    parser.add_argument("--camera-id", default="cam-1")
    args = parser.parse_args()
    sync_slots(args.file, args.camera_id)
