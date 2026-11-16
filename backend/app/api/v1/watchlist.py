from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistResponse
from app.services.redis_service import redis_service

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.get("", response_model=List[WatchlistResponse])
def get_watchlist(
    response: Response,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search plate number"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(Watchlist)
    if is_active is not None:
        query = query.filter(Watchlist.is_active == is_active)
    if search:
        cleaned = search.strip().upper().replace(" ", "").replace("-", "")
        query = query.filter(Watchlist.plate_number.contains(cleaned))

    total = query.count()
    items = query.order_by(Watchlist.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist_entry(entry: WatchlistCreate, db: Session = Depends(get_db)):
    normalized_plate = entry.plate_number.strip().upper().replace(" ", "").replace("-", "")
    existing = db.query(Watchlist).filter(Watchlist.plate_number == normalized_plate).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License plate {normalized_plate} already exists in watchlist."
        )

    db_entry = Watchlist(
        plate_number=normalized_plate,
        reason=entry.reason,
        added_by=entry.added_by,
        is_active=entry.is_active,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    if db_entry.is_active:
        redis_service.add_watchlist_plate(normalized_plate)

    return db_entry

@router.get("/{id}", response_model=WatchlistResponse)
def get_watchlist_entry(id: int, db: Session = Depends(get_db)):
    entry = db.query(Watchlist).filter(Watchlist.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return entry

@router.put("/{id}", response_model=WatchlistResponse)
def update_watchlist_entry(id: int, update_data: WatchlistUpdate, db: Session = Depends(get_db)):
    entry = db.query(Watchlist).filter(Watchlist.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    if update_data.reason is not None:
        entry.reason = update_data.reason
    if update_data.added_by is not None:
        entry.added_by = update_data.added_by
    if update_data.is_active is not None:
        entry.is_active = update_data.is_active
        if entry.is_active:
            redis_service.add_watchlist_plate(entry.plate_number)
        else:
            redis_service.remove_watchlist_plate(entry.plate_number)

    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_entry(id: int, db: Session = Depends(get_db)):
    entry = db.query(Watchlist).filter(Watchlist.id == id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    redis_service.remove_watchlist_plate(entry.plate_number)
    db.delete(entry)
    db.commit()
    return None
