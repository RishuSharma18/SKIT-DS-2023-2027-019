from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class AlertBase(BaseModel):
    alert_type: str = Field(..., example="STOLEN_VEHICLE")
    severity: str = Field(default="MEDIUM", example="HIGH")
    plate_number: Optional[str] = None
    slot_id: Optional[str] = None
    camera_id: str = "cam-1"
    snapshot_url: Optional[str] = None
    message: Optional[str] = None

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    alert_id: str
    is_acknowledged: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
