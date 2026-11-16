from typing import Optional, Any
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class AIEventPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str = Field(..., validation_alias=AliasChoices("type", "event_type"), example="entry")
    track_id: Optional[int] = Field(None, validation_alias=AliasChoices("track_id", "trackId"), example=101)
    plate_number: Optional[str] = Field(None, validation_alias=AliasChoices("plate_number", "plate"), example="RJ14AB1234")
    vehicle_category: Optional[str] = Field(None, validation_alias=AliasChoices("vehicle_category", "vehicleType"), example="COMPACT_CAR")
    slot_id: Optional[str] = Field(None, validation_alias=AliasChoices("slot_id", "slotId"), example="A-01")
    camera_id: Optional[str] = Field("cam-1", validation_alias=AliasChoices("camera_id", "cameraId"), example="cam-1")
    snapshot: Optional[str] = None
    snapshot_url: Optional[str] = None
    alert_type: Optional[str] = None
    event_id: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None

class AIEventResponse(BaseModel):
    success: bool = True
    event_type: str
    message: str
    session: Optional[dict[str, Any]] = None
    alert: Optional[dict[str, Any]] = None
    allocation: Optional[dict[str, Any]] = None
    slot: Optional[dict[str, Any]] = None
