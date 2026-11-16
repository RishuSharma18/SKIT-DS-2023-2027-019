import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models.parking_slot import ParkingSlot
from app.models.watchlist import Watchlist
from app.services.redis_service import redis_service

SAMPLE_SLOTS = [
    # ZONE-A: Two Wheelers & Compact Cars (Front Row)
    {
        "slot_id": "A-01",
        "zone": "ZONE-A",
        "allowed_category": "TWO_WHEELER",
        "status": "AVAILABLE",
        "polygon_coords": [[50, 100], [120, 100], [120, 220], [50, 220]],
    },
    {
        "slot_id": "A-02",
        "zone": "ZONE-A",
        "allowed_category": "TWO_WHEELER",
        "status": "AVAILABLE",
        "polygon_coords": [[130, 100], [200, 100], [200, 220], [130, 220]],
    },
    {
        "slot_id": "A-03",
        "zone": "ZONE-A",
        "allowed_category": "COMPACT_CAR",
        "status": "AVAILABLE",
        "polygon_coords": [[220, 100], [340, 100], [340, 260], [220, 260]],
    },
    {
        "slot_id": "A-04",
        "zone": "ZONE-A",
        "allowed_category": "COMPACT_CAR",
        "status": "AVAILABLE",
        "polygon_coords": [[360, 100], [480, 100], [480, 260], [360, 260]],
    },
    # ZONE-B: Compact Cars & SUVs (Mid Section)
    {
        "slot_id": "B-01",
        "zone": "ZONE-B",
        "allowed_category": "COMPACT_CAR",
        "status": "AVAILABLE",
        "polygon_coords": [[50, 320], [170, 320], [170, 480], [50, 480]],
    },
    {
        "slot_id": "B-02",
        "zone": "ZONE-B",
        "allowed_category": "COMPACT_CAR",
        "status": "AVAILABLE",
        "polygon_coords": [[190, 320], [310, 320], [310, 480], [190, 480]],
    },
    {
        "slot_id": "B-03",
        "zone": "ZONE-B",
        "allowed_category": "SUV_SEDAN",
        "status": "AVAILABLE",
        "polygon_coords": [[330, 320], [470, 320], [470, 500], [330, 500]],
    },
    {
        "slot_id": "B-04",
        "zone": "ZONE-B",
        "allowed_category": "SUV_SEDAN",
        "status": "AVAILABLE",
        "polygon_coords": [[490, 320], [630, 320], [630, 500], [490, 500]],
    },
    # ZONE-C: Large SUVs & Heavy Commercial Vehicles (Rear Section)
    {
        "slot_id": "C-01",
        "zone": "ZONE-C",
        "allowed_category": "SUV_SEDAN",
        "status": "AVAILABLE",
        "polygon_coords": [[50, 550], [200, 550], [200, 750], [50, 750]],
    },
    {
        "slot_id": "C-02",
        "zone": "ZONE-C",
        "allowed_category": "HEAVY_VEHICLE",
        "status": "AVAILABLE",
        "polygon_coords": [[230, 550], [430, 550], [430, 800], [230, 800]],
    },
    {
        "slot_id": "C-03",
        "zone": "ZONE-C",
        "allowed_category": "HEAVY_VEHICLE",
        "status": "AVAILABLE",
        "polygon_coords": [[460, 550], [660, 550], [660, 800], [460, 800]],
    },
]

SAMPLE_WATCHLIST = [
    {
        "plate_number": "RJ14AB1234",
        "reason": "STOLEN - FIR #402/24 Jaipur Central",
        "added_by": "state_police",
        "is_active": True,
    },
    {
        "plate_number": "DL01XY9999",
        "reason": "WANTED - Traffic Felony Incident",
        "added_by": "traffic_authority",
        "is_active": True,
    },
    {
        "plate_number": "HR26DK2001",
        "reason": "SUSPICIOUS - Vehicle associated with theft ring",
        "added_by": "security_admin",
        "is_active": True,
    },
]

def seed():
    print("Initializing DB tables...")
    init_db()

    db = SessionLocal()
    try:
        print("\n--- Seeding Parking Slots ---")
        for s in SAMPLE_SLOTS:
            existing = db.query(ParkingSlot).filter(ParkingSlot.slot_id == s["slot_id"]).first()
            if not existing:
                slot = ParkingSlot(**s)
                db.add(slot)
                print(f"  + Added Slot: {s['slot_id']} ({s['zone']}, {s['allowed_category']})")
            else:
                print(f"  * Slot {s['slot_id']} already exists")

        print("\n--- Seeding Watchlist ---")
        active_plates = set()
        for w in SAMPLE_WATCHLIST:
            normalized = w["plate_number"].strip().upper().replace(" ", "").replace("-", "")
            active_plates.add(normalized)
            existing = db.query(Watchlist).filter(Watchlist.plate_number == normalized).first()
            if not existing:
                item = Watchlist(
                    plate_number=normalized,
                    reason=w["reason"],
                    added_by=w["added_by"],
                    is_active=w["is_active"],
                )
                db.add(item)
                print(f"  + Added Watchlist Plate: {normalized} ({w['reason']})")
            else:
                print(f"  * Watchlist plate {normalized} already exists")

        db.commit()

        # Cache in Redis
        redis_service.populate_watchlist_cache(active_plates)
        print(f"\nCached {len(active_plates)} watchlist plates in Redis/memory.")
        print("\nSeed completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
