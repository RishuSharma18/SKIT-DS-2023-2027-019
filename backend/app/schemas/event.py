from typing import Optional, Any
from pydantic import BaseModel, Field

class AIEventPayload(BaseModel):
    type: str = Field(..., example="entry")
    track_id: Optional[int] = Field(None, alias="trackId", example=101)
    plate_number: Optional[str] = Field(None, alias="plate", example="RJ14AB1234")
    vehicle_category: Optional[str] = Field(None, alias="vehicleType", example="COMPACT_CAR")
    slot_id: Optional[str] = Field(None, alias="slotId", example="A-01")
    camera_id: Optional[str] = Field("cam-1", alias="cameraId", example="cam-1")
    snapshot: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None

    class Config:
        populate_by_name = True

class AIEventResponse(BaseModel):
    success: bool = True
    event_type: str
    message: str
    session: Optional[dict[str, Any]] = None
    alert: Optional[dict[str, Any]] = None
    allocation: Optional[dict[str, Any]] = None
    slot: Optional[dict[str, Any]] = None
