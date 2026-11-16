import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type = Column(String(50), nullable=False, index=True)  # STOLEN_VEHICLE, ACCIDENT, WRONG_PARKING, OVERSTAY
    severity = Column(String(20), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    plate_number = Column(String(32), index=True, nullable=True)
    slot_id = Column(String(50), nullable=True)
    camera_id = Column(String(50), default="cam-1")
    snapshot_url = Column(String(512), nullable=True)
    message = Column(String(512), nullable=True)
    is_acknowledged = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "plate_number": self.plate_number,
            "slot_id": self.slot_id,
            "camera_id": self.camera_id,
            "snapshot_url": self.snapshot_url,
            "message": self.message,
            "is_acknowledged": self.is_acknowledged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
