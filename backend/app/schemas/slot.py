from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class SlotBase(BaseModel):
    slot_id: str = Field(..., example="A-01")
    camera_id: str = Field(default="cam-1", example="cam-1")
    zone: str = Field(default="ZONE-A", example="ZONE-A")
    allowed_category: str = Field(default="COMPACT_CAR", example="COMPACT_CAR")
    status: str = Field(default="AVAILABLE", example="AVAILABLE")
    polygon_coords: Optional[Any] = None
    current_track_id: Optional[int] = None

class SlotCreate(BaseModel):
    slot_id: str
    camera_id: str = "cam-1"
    zone: str = "ZONE-A"
    allowed_category: str = "COMPACT_CAR"
    status: Optional[str] = "AVAILABLE"
    polygon_coords: Optional[Any] = None

class SlotUpdate(BaseModel):
    camera_id: Optional[str] = None
    zone: Optional[str] = None
    allowed_category: Optional[str] = None
    status: Optional[str] = None
    polygon_coords: Optional[Any] = None
    current_track_id: Optional[int] = None

class SlotResponse(SlotBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
