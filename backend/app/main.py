import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import init_db, SessionLocal
from app.models.watchlist import Watchlist
from app.services.redis_service import redis_service
from app.services.websocket_manager import ws_manager
from app.services.overstay_worker import run_overstay_checker

from app.api.v1.events import router as events_router
from app.api.v1.slots import router as slots_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.watchlist import router as watchlist_router
from app.api.v1.alerts import router as alerts_router
from app.api.legacy_compat import legacy_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cctv-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    init_db()

    # Pre-populate watchlist in Redis cache for sub-millisecond lookup
    db = SessionLocal()
    try:
        active_plates = {
            w.plate_number
            for w in db.query(Watchlist).filter(Watchlist.is_active == True).all()
        }
        redis_service.populate_watchlist_cache(active_plates)
        logger.info(f"Loaded {len(active_plates)} active watchlist plates into fast-lookup cache.")
    except Exception as exc:
        logger.warning(f"Failed to pre-populate watchlist cache: {exc}")
    finally:
        db.close()

    stop_event: Optional[asyncio.Event] = None
    worker_task: Optional[asyncio.Task] = None

    if settings.ENABLE_OVERSTAY_WORKER:
        stop_event = asyncio.Event()
        worker_task = asyncio.create_task(run_overstay_checker(stop_event))
        logger.info("Background overstay worker started.")

    logger.info("Application startup completed successfully.")

    try:
        yield
    finally:
        if stop_event and worker_task:
            logger.info("Shutting down background tasks...")
            stop_event.set()
            worker_task.cancel()
            try:
                await asyncio.wait_for(worker_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            logger.info("Background tasks stopped.")
        logger.info("Application shutdown completed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade backend service orchestrating smart parking management, "
        "stolen-vehicle checks via Redis cache, intelligent slot allocation, "
        "background duration/overstay tracking, and real-time WebSocket dashboard alerts."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Static file serving for uploads (snapshots)
uploads_dir: Path = settings.UPLOADS_DIR
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Include API v1 Routers
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(slots_router, prefix=settings.API_V1_STR)
app.include_router(sessions_router, prefix=settings.API_V1_STR)
app.include_router(watchlist_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)

# Include Legacy Compatibility Router
app.include_router(legacy_router)

# WebSocket Endpoint: /ws/events (FR-17, FR-18)
@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint pushing live slot updates, entry/exit logs,
    and alerts to all connected dashboard clients.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket client error: {exc}")
        ws_manager.disconnect(websocket)

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs")
