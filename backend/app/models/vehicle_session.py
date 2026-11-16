import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from app.database import Base

class VehicleSession(Base):
    __tablename__ = "vehicle_sessions"

    session_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id = Column(Integer, index=True, nullable=False)
    plate_number = Column(String(32), index=True, nullable=True)
    vehicle_category = Column(String(50), nullable=False, default="COMPACT_CAR")
    assigned_slot_id = Column(String(50), ForeignKey("parking_slots.slot_id"), nullable=True)
    actual_slot_id = Column(String(50), ForeignKey("parking_slots.slot_id"), nullable=True)
    camera_id = Column(String(50), default="cam-1")
    entry_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    exit_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, default=0.0)
    status = Column(String(32), default="ACTIVE", index=True)  # ACTIVE, COMPLETED, OVERSTAY
    overstay_alerted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "track_id": self.track_id,
            "plate_number": self.plate_number,
            "vehicle_category": self.vehicle_category,
            "assigned_slot_id": self.assigned_slot_id,
            "actual_slot_id": self.actual_slot_id,
            "camera_id": self.camera_id,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "duration_minutes": round(self.duration_minutes, 2) if self.duration_minutes else 0.0,
            "status": self.status,
            "overstay_alerted": self.overstay_alerted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
