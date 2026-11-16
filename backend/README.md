# Production-Grade Backend Service

Enterprise backend service built with Python FastAPI, PostgreSQL, Redis, and WebSockets orchestrating smart parking management, sub-millisecond stolen-vehicle checks, smart slot allocation, background duration/overstay tracking, and real-time dashboard notifications.

## Key Features
- **Automatic Swagger/OpenAPI Docs**: Interactive UI at `/docs`, ReDoc at `/redoc`.
- **PostgreSQL Schema & Alembic Migrations**: Comprehensive relational schema for slots, sessions, watchlist, and alerts.
- **Sub-millisecond Watchlist Matching**: Cached in Redis with plate normalization (`RJ14AB1234`).
- **Smart Slot Allocation Engine**: Nearest available slot matching with fallback hierarchy.
- **Event Idempotency**: Deduplicates incoming frames for the same `track_id` via Redis.
- **Overstay Background Worker**: Background task checking active sessions every 60 seconds against `MAX_ALLOWED_DURATION`.
- **Real-time WebSockets**: `/ws/events` broadcasting live slot occupancies and high-priority alerts.
- **Static Media Serving**: `/uploads/` serves incident snapshots.
- **Legacy Compatibility**: Full support for existing React dashboard via `/api/...` routes.

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations & Seed
```bash
alembic upgrade head
python scripts/seed.py
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```
Open [http://localhost:5000/docs](http://localhost:5000/docs) in your browser for interactive API exploration.

### 4. Run Automated Test Suite
```bash
python tests/run_tests.py
```

---

## Docker Setup

Start PostgreSQL, Redis, and Mongo with Docker Compose:
```bash
docker compose up -d
```

---

## API Summary

See full documentation at [docs/API.md](../docs/API.md) or live Swagger UI at `/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/docs` | `GET` | Interactive Swagger UI documentation |
| `/api/v1/ai-events` | `POST` | Ingests AI camera events with idempotency & watchlist check |
| `/api/v1/slots/allocate` | `POST` | Smart slot allocation engine with category fallback |
| `/api/v1/slots` | `GET`, `POST` | Parking slots configuration and status |
| `/api/v1/slots/{slot_id}` | `GET`, `PATCH`, `DELETE` | Single slot inspection and updates |
| `/api/v1/sessions` | `GET` | Filtered and paginated vehicle parking history |
| `/api/v1/watchlist` | `GET`, `POST` | Stolen/wanted vehicle plate watchlist CRUD |
| `/api/v1/alerts` | `GET` | Incident and safety alerts with pagination |
| `/api/v1/alerts/{id}/ack` | `PATCH` | Acknowledge alert |
| `/ws/events` | `WebSocket` | Real-time WebSocket event stream |
