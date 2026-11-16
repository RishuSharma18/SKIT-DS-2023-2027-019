import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    target_url = settings.DATABASE_URL
    connect_args = {}

    if target_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(target_url, connect_args=connect_args)

    try:
        # 1-second timeout so it fails immediately if Postgres daemon is offline
        engine = create_engine(target_url, pool_pre_ping=True, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            pass
        logger.info(f"Connected to primary database: {target_url}")
        return engine
    except Exception as exc:
        if settings.ENABLE_SQLITE_FALLBACK:
            logger.warning(
                f"Failed to connect to primary DB ({exc}). Falling back to SQLite: {settings.SQLITE_URL}"
            )
            connect_args["check_same_thread"] = False
            return create_engine(settings.SQLITE_URL, connect_args=connect_args)
        raise exc

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models.parking_slot import ParkingSlot
    from app.models.vehicle_session import VehicleSession
    from app.models.watchlist import Watchlist
    from app.models.alert import Alert
    Base.metadata.create_all(bind=engine)
