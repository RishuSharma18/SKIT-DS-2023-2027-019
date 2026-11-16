# Production-Grade Backend Service

The active backend is the Python FastAPI service in `backend/app`. The older Express/MongoDB code in `backend/src` is retained for reference but is not part of the current application run path.

## Key Features
- **Automatic Swagger/OpenAPI Docs**: Interactive UI at `/docs`, ReDoc at `/redoc`.
- **PostgreSQL Schema & Alembic Migrations**: Comprehensive relational schema for slots, sessions, watchlist, and alerts.
- **Sub-millisecond Watchlist Matching**: Cached in Redis with plate normalization (`RJ14AB1234`).
- **Smart Slot Allocation Engine**: Uses the polygon centroid nearest to an optional camera-frame point, with category fallback; without a point it uses deterministic zone/slot ordering.
- **Event Idempotency**: Deduplicates entry frames by camera and track ID via Redis.
- **Overstay Background Worker**: Background task checking active sessions every 60 seconds against `MAX_ALLOWED_DURATION`.
- **Real-time WebSockets**: `/ws/events` broadcasting live slot occupancies and high-priority alerts.
- **Static Media Serving**: `/uploads/` serves incident snapshots.
- **Plate OCR Proxy**: `/api/v1/ocr/plate` validates upload size/type and forwards photos to the local AI service without storing them.
- **Legacy Compatibility**: Full support for existing React dashboard via `/api/...` routes.

---

## Quickstart

### 1. Install Dependencies
```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
```
Set `AI_API_KEY` to a non-default secret and configure the same value in `ai-service/.env`. The backend requires this key for both AI event routes and camera-zone reads.
If PostgreSQL is not running, configure `DATABASE_URL=sqlite:///./cctv_parking.db` in `backend/.env` before running Alembic.

### 2. Run Database Migrations & Seed

For a fresh database:

```bash
alembic upgrade head
python scripts/seed.py
python scripts/sync_camera_zones.py --camera-id cam-1
```

If an older app version already created the tables before Alembic was introduced, and the
database matches the original schema, record that baseline once before upgrading:

```bash
alembic stamp 001_initial_schema
alembic upgrade head
```

This preserves existing data and applies later migrations. Do not stamp a fresh database or
one that already has an Alembic revision.

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

Start PostgreSQL and Redis for the FastAPI backend. MongoDB belongs only to the legacy Express code and is not required:
```bash
docker compose up -d postgres redis
```

---

## API Summary

See full documentation at [docs/API.md](../docs/API.md) or live Swagger UI at `/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/docs` | `GET` | Interactive Swagger UI documentation |
| `/api/v1/ai-events` | `POST` | Ingests AI camera events with idempotency & watchlist check |
| `/api/v1/cameras/{camera_id}/zones` | `GET` | Authenticated camera slot polygons for the AI service |
| `/api/v1/ocr/plate` | `POST` | In-memory plate-photo OCR proxy to the configured AI service |
| `/api/v1/slots/allocate` | `POST` | Slot allocation; accepts optional `camera_id` and `reference_point` |
| `/api/v1/slots` | `GET`, `POST` | Parking slots configuration and status |
| `/api/v1/slots/{slot_id}` | `GET`, `PATCH`, `DELETE` | Single slot inspection and updates |
| `/api/v1/sessions` | `GET` | Filtered and paginated vehicle parking history |
| `/api/v1/watchlist` | `GET`, `POST` | Stolen/wanted vehicle plate watchlist CRUD |
| `/api/v1/alerts` | `GET` | Incident and safety alerts with pagination |
| `/api/v1/alerts/{id}/ack` | `PATCH` | Acknowledge alert |
| `/ws/events` | `WebSocket` | Real-time WebSocket event stream |
