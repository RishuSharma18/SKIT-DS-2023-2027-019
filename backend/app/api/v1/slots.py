from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.parking_slot import ParkingSlot
from app.schemas.slot import SlotCreate, SlotUpdate, SlotResponse
from app.schemas.allocation import AllocateRequest, AllocateResponse
from app.services.allocation_engine import allocate_nearest_slot
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/slots", tags=["Parking Slots"])

@router.get("", response_model=List[SlotResponse])
def get_slots(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    zone: Optional[str] = Query(None, description="Filter by parking zone (e.g. ZONE-A)"),
    status: Optional[str] = Query(None, description="Filter by status (AVAILABLE, OCCUPIED, RESERVED, VIOLATION)"),
    allowed_category: Optional[str] = Query(None, description="Filter by allowed vehicle category"),
    configured_only: bool = Query(False, description="Only return slots with a configured camera polygon"),
    db: Session = Depends(get_db)
):
    query = db.query(ParkingSlot)
    if configured_only:
        query = query.filter(
            ParkingSlot.polygon_coords.isnot(None),
            cast(ParkingSlot.polygon_coords, String) != "null",
        )
    if camera_id:
        query = query.filter(ParkingSlot.camera_id == camera_id)
    if zone:
        query = query.filter(ParkingSlot.zone == zone)
    if status:
        query = query.filter(ParkingSlot.status == status.upper())
    if allowed_category:
        query = query.filter(ParkingSlot.allowed_category == allowed_category.upper())

    return query.order_by(ParkingSlot.zone.asc(), ParkingSlot.slot_id.asc()).all()

@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(slot: SlotCreate, db: Session = Depends(get_db)):
    existing = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot.slot_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot with ID '{slot.slot_id}' already exists."
        )

    db_slot = ParkingSlot(
        slot_id=slot.slot_id,
        camera_id=slot.camera_id,
        zone=slot.zone,
        allowed_category=slot.allowed_category,
        status=slot.status or "AVAILABLE",
        polygon_coords=slot.polygon_coords,
    )
    db.add(db_slot)
    db.commit()
    db.refresh(db_slot)

    slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
    await ws_manager.broadcast_slot_update(slots)
    return db_slot

@router.get("/{slot_id}", response_model=SlotResponse)
def get_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
    return slot

@router.patch("/{slot_id}", response_model=SlotResponse)
async def update_slot(slot_id: str, updates: SlotUpdate, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")

    if updates.zone is not None:
        slot.zone = updates.zone
    if updates.camera_id is not None:
        slot.camera_id = updates.camera_id
    if updates.allowed_category is not None:
        slot.allowed_category = updates.allowed_category
    if updates.status is not None:
        slot.status = updates.status.upper()
    if updates.polygon_coords is not None:
        slot.polygon_coords = updates.polygon_coords
    if updates.current_track_id is not None:
        slot.current_track_id = updates.current_track_id

    db.commit()
    db.refresh(slot)

    slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
    await ws_manager.broadcast_slot_update(slots)
    return slot

@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")

    db.delete(slot)
    db.commit()

    slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
    await ws_manager.broadcast_slot_update(slots)
    return None

# FR-09, FR-10: Smart Slot Allocation Engine
@router.post("/allocate", response_model=AllocateResponse)
async def allocate_slot_endpoint(request: AllocateRequest, db: Session = Depends(get_db)):
    """
    Given vehicle_category, find nearest AVAILABLE slot matching exact category
    (with fallback to next larger category). Mark slot RESERVED and return
    recommended slot_id and navigation zone.
    """
    slot, msg = allocate_nearest_slot(
        db,
        request.vehicle_category,
        track_id=request.track_id,
        reserve=True,
        camera_id=request.camera_id,
        reference_point=request.reference_point,
    )
    if not slot:
        return AllocateResponse(
            recommended_slot_id=None,
            camera_id=request.camera_id,
            zone=None,
            allowed_category=None,
            status=None,
            message=msg
        )

    slots = [s.to_dict() for s in db.query(ParkingSlot).all()]
    await ws_manager.broadcast_slot_update(slots)

    return AllocateResponse(
        recommended_slot_id=slot.slot_id,
        camera_id=slot.camera_id,
        zone=slot.zone,
        allowed_category=slot.allowed_category,
        status=slot.status,
        message=msg
    )
