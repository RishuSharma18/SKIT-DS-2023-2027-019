from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertResponse
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["Alerts & Safety"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    response: Response,
    alert_type: Optional[str] = Query(None, alias="type", description="Filter by alert type (STOLEN_VEHICLE, ACCIDENT, WRONG_PARKING, OVERSTAY)"),
    severity: Optional[str] = Query(None, description="Filter by severity (HIGH, MEDIUM, LOW)"),
    is_acknowledged: Optional[bool] = Query(None, alias="acknowledged", description="Filter by acknowledgment state"),
    plate_number: Optional[str] = Query(None, alias="plate", description="Filter by plate number"),
    slot_id: Optional[str] = Query(None, description="Filter by slot ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)

    if alert_type and alert_type.lower() != "all":
        query = query.filter(Alert.alert_type == alert_type.upper())
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if is_acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == is_acknowledged)
    if plate_number:
        cleaned = plate_number.strip().upper().replace(" ", "").replace("-", "")
        query = query.filter(Alert.plate_number.contains(cleaned))
    if slot_id:
        query = query.filter(Alert.slot_id == slot_id)

    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.patch("/{id}/ack", response_model=AlertResponse)
async def acknowledge_alert(id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_acknowledged = True
    db.commit()
    db.refresh(alert)

    await ws_manager.broadcast("alert:ack", alert.to_dict())
    return alert
