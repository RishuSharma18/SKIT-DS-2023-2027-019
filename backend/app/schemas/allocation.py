from typing import Optional, Tuple
from pydantic import BaseModel, Field, FiniteFloat

class AllocateRequest(BaseModel):
    vehicle_category: str = Field(default="COMPACT_CAR", example="COMPACT_CAR")
    track_id: Optional[int] = None
    camera_id: Optional[str] = None
    reference_point: Optional[Tuple[FiniteFloat, FiniteFloat]] = Field(
        default=None,
        description="Optional (x, y) camera-frame point used to select the geometrically nearest slot.",
    )

class AllocateResponse(BaseModel):
    recommended_slot_id: Optional[str] = None
    camera_id: Optional[str] = None
    zone: Optional[str] = None
    allowed_category: Optional[str] = None
    status: Optional[str] = None
    message: str = "Slot allocated successfully"
