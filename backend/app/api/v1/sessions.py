from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.vehicle_session import VehicleSession
from app.schemas.session import SessionResponse

router = APIRouter(prefix="/sessions", tags=["Vehicle Sessions"])

@router.get("", response_model=List[SessionResponse])
def get_sessions(
    response: Response,
    plate_number: Optional[str] = Query(None, alias="plate", description="Filter by plate number (partial match)"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, COMPLETED, OVERSTAY)"),
    vehicle_category: Optional[str] = Query(None, description="Filter by vehicle category"),
    assigned_slot_id: Optional[str] = Query(None, description="Filter by assigned slot ID"),
    actual_slot_id: Optional[str] = Query(None, description="Filter by actual parked slot ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    query = db.query(VehicleSession)

    if plate_number:
        cleaned = plate_number.strip().upper().replace(" ", "").replace("-", "")
        query = query.filter(VehicleSession.plate_number.contains(cleaned))
    if status:
        query = query.filter(VehicleSession.status == status.upper())
    if vehicle_category:
        query = query.filter(VehicleSession.vehicle_category == vehicle_category.upper())
    if assigned_slot_id:
        query = query.filter(VehicleSession.assigned_slot_id == assigned_slot_id)
    if actual_slot_id:
        query = query.filter(VehicleSession.actual_slot_id == actual_slot_id)

    total = query.count()
    items = (
        query.order_by(VehicleSession.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(VehicleSession).filter(VehicleSession.session_id == session_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Vehicle session not found")
    return session
