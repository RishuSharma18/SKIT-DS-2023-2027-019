from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    slot_id = Column(String(50), primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, default="cam-1", server_default="cam-1", index=True)
    zone = Column(String(50), index=True, nullable=False, default="ZONE-A")
    allowed_category = Column(String(50), nullable=False, default="COMPACT_CAR")
    status = Column(String(50), nullable=False, default="AVAILABLE", index=True)
    polygon_coords = Column(JSON(none_as_null=True), nullable=True)
    current_track_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "slot_id": self.slot_id,
            "camera_id": self.camera_id,
            "zone": self.zone,
            "allowed_category": self.allowed_category,
            "status": self.status,
            "polygon_coords": self.polygon_coords,
            "current_track_id": self.current_track_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
