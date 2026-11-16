from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(32), unique=True, index=True, nullable=False)
    reason = Column(String(255), nullable=False, default="STOLEN")
    added_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "reason": self.reason,
            "added_by": self.added_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }
