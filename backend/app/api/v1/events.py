from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.dependencies import verify_api_key
from app.database import get_db
from app.schemas.event import AIEventPayload, AIEventResponse
from app.services.event_ingestion import process_ai_event

router = APIRouter(prefix="/ai-events", tags=["AI Telemetry Ingestion"])

@router.post("", response_model=AIEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_ai_event(
    payload: AIEventPayload,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key)
):
    """
    Ingests telemetry events from AI services (YOLO tracker, plate OCR, crash heuristic).
    Performs idempotency check, plate normalization, Redis watchlist lookup,
    automatic slot reservation, and real-time WebSocket broadcast.
    """
    result = await process_ai_event(db, payload)
    return AIEventResponse(
        success=result.get("success", True),
        event_type=result.get("event_type", payload.type),
        message=result.get("message", "Event processed successfully"),
        session=result.get("session"),
        alert=result.get("alert"),
        allocation=result.get("allocation"),
        slot=result.get("slot"),
    )
