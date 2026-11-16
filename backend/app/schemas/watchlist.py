from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class WatchlistBase(BaseModel):
    plate_number: str = Field(..., example="RJ14AB1234")
    reason: str = Field(default="STOLEN", example="STOLEN")
    added_by: str = Field(default="security_admin", example="security_admin")
    is_active: bool = True

class WatchlistCreate(WatchlistBase):
    pass

class WatchlistUpdate(BaseModel):
    reason: Optional[str] = None
    added_by: Optional[str] = None
    is_active: Optional[bool] = None

class WatchlistResponse(WatchlistBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
