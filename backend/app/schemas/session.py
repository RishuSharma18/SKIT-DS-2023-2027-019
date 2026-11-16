from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class SessionResponse(BaseModel):
    session_id: str
    track_id: int
    plate_number: Optional[str] = None
    vehicle_category: str
    assigned_slot_id: Optional[str] = None
    actual_slot_id: Optional[str] = None
    camera_id: str = "cam-1"
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    duration_minutes: float = 0.0
    status: str
    overstay_alerted: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
