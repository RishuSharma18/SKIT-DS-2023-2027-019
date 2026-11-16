from typing import Optional
from pydantic import BaseModel, Field

class AllocateRequest(BaseModel):
    vehicle_category: str = Field(default="COMPACT_CAR", example="COMPACT_CAR")
    track_id: Optional[int] = None

class AllocateResponse(BaseModel):
    recommended_slot_id: Optional[str] = None
    zone: Optional[str] = None
    allowed_category: Optional[str] = None
    status: Optional[str] = None
    message: str = "Slot allocated successfully"
