# API Reference Documentation

Smart CCTV Parking & Vehicle Safety System Backend REST API, OpenAPI/Swagger Interface, and Real-Time WebSocket Telemetry.

- **Base URL**: `http://localhost:5000`
- **Interactive Swagger UI**: `http://localhost:5000/docs`
- **Interactive ReDoc**: `http://localhost:5000/redoc`
- **OpenAPI JSON Spec**: `http://localhost:5000/openapi.json`
- **Default Port**: `5000`
- **Content-Type**: `application/json`
- **Max JSON Payload**: `10MB` (accommodates base64 snapshot uploads)

---

## Table of Contents
1. [Interactive OpenAPI / Swagger Documentation](#interactive-openapi--swagger-documentation)
2. [Database Schema (PostgreSQL) & Migrations](#database-schema-postgresql--migrations)
3. [Redis Caching & Event Idempotency](#redis-caching--event-idempotency)
4. [Authentication](#authentication)
5. [Core REST API Endpoints (/api/v1)](#core-rest-api-endpoints-apiv1)
   - [POST /api/v1/ai-events (Event Ingestion & Watchlist Matching)](#post-apiv1ai-events)
   - [POST /api/v1/slots/allocate (Smart Slot Allocation Engine)](#post-apiv1slotsallocate)
   - [Parking Slots CRUD (/api/v1/slots)](#parking-slots-crud-apiv1slots)
   - [Camera Zones (/api/v1/cameras/:cameraId/zones)](#camera-zones)
   - [Plate OCR (/api/v1/ocr/plate)](#plate-ocr-apiv1ocrplate)
   - [Vehicle Sessions History & Filters (/api/v1/sessions)](#vehicle-sessions-history--filters-apiv1sessions)
   - [Watchlist Management (/api/v1/watchlist)](#watchlist-management-apiv1watchlist)
   - [Alerts & Acknowledgment (/api/v1/alerts)](#alerts--acknowledgment-apiv1alerts)
6. [Real-Time WebSocket (/ws/events)](#real-time-websocket-wsevents)
7. [Duration & Overstay Background Worker](#duration--overstay-background-worker)
8. [Legacy Frontend Compatibility Endpoints (/api)](#legacy-frontend-compatibility-endpoints-api)
   - [GET /api/health](#get-apihealth)
   - [GET /api/stats](#get-apistats)
   - [GET /api/analytics/hourly](#get-apianalyticshourly)
   - [GET /api/slots](#get-apislots)
   - [GET /api/slots/recommend](#get-apislotsrecommend)
   - [GET /api/sessions](#get-apisessions)
   - [GET /api/alerts & PATCH /api/alerts/:id/ack](#get-apialerts)
   - [Watchlist Legacy (/api/watchlist)](#watchlist-legacy-apiwatchlist)
   - [Event Ingestion Legacy (/api/events)](#event-ingestion-legacy-apievents)
9. [Static Media Storage (/uploads)](#static-media-storage-uploads)

---

## Interactive OpenAPI / Swagger Documentation

The backend service automatically generates full OpenAPI 3.1.0 specifications and interactive Swagger documentation:
- **Swagger UI**: Visit `http://localhost:5000/docs` in your browser to test all endpoints interactively.
- **ReDoc**: Accessible at `http://localhost:5000/redoc` for detailed schemas and parameter tables.
- **Raw OpenAPI Spec**: `GET http://localhost:5000/openapi.json`.

---

## Database Schema (PostgreSQL / SQLite) & Migrations

The database schema is managed via **Alembic** migrations (`backend/alembic/`):
```bash
cd backend
alembic upgrade head
python scripts/seed.py
```

### Table Definitions:
1. **`parking_slots`**:
   - `slot_id` (String PK): Unique slot identifier (e.g. `A-01`, `B-03`).
   - `camera_id` (String, indexed): Camera whose coordinate space owns this polygon.
   - `zone` (String, indexed): Zone name (e.g. `ZONE-A`, `ZONE-B`, `ZONE-C`).
   - `allowed_category` (String): Allowed vehicle type (`TWO_WHEELER`, `COMPACT_CAR`, `SUV_SEDAN`, `HEAVY_VEHICLE`).
   - `status` (String, indexed): Slot occupancy (`AVAILABLE`, `OCCUPIED`, `RESERVED`, `VIOLATION`).
   - `polygon_coords` (JSONB / JSON): Array of polygon boundary vertices `[[x1, y1], [x2, y2], ...]`.
   - `current_track_id` (Integer, nullable): Current vehicle track ID occupying the space.
   - `created_at`, `updated_at`: Timestamps.

2. **`vehicle_sessions`** (FR-11, FR-16):
   - `session_id` (String PK, UUID): Session identifier.
   - `track_id` (Integer, indexed): ByteTrack / YOLO tracker ID.
   - `plate_number` (String, indexed): Recognized license plate (normalized).
   - `vehicle_category` (String): `TWO_WHEELER`, `COMPACT_CAR`, `SUV_SEDAN`, `HEAVY_VEHICLE`.
   - `assigned_slot_id` (String FK -> parking_slots): Recommended / reserved slot ID.
   - `actual_slot_id` (String FK -> parking_slots): Physical slot parked in.
   - `entry_time`: ISO8601 timestamp of vehicle entry.
   - `exit_time`: ISO8601 timestamp of vehicle exit.
   - `duration_minutes`: Exact parking duration in minutes calculated on exit.
   - `status` (String, indexed): `ACTIVE`, `COMPLETED`, `OVERSTAY`.
   - `overstay_alerted` (Boolean): Flag to prevent duplicate overstay notifications.

3. **`watchlist`** (FR-08):
   - `id` (Integer PK): Identifier.
   - `plate_number` (String, unique indexed): Normalized vehicle registration plate.
   - `reason` (String): Flag reason (`STOLEN`, `WANTED`, `SUSPICIOUS`, etc.).
   - `added_by` (String): Operator or agency identifier.
   - `created_at`: Timestamp.
   - `is_active` (Boolean, indexed): Active tracking state.

4. **`alerts`** (FR-15):
   - `alert_id` (String PK, UUID): Unique incident identifier.
   - `alert_type` (String, indexed): `STOLEN_VEHICLE`, `ACCIDENT`, `WRONG_PARKING`, `OVERSTAY`.
   - `severity` (String): `HIGH`, `MEDIUM`, `LOW`.
   - `plate_number` (String, nullable): Associated vehicle plate.
   - `slot_id` (String, nullable): Slot associated with violation.
   - `camera_id` (String, nullable): Detecting edge camera.
   - `snapshot_url` (String, nullable): Evidence URL; AI snapshots use `/media/alerts/`, while backend base64 uploads use `/uploads/`.
   - `message` (String): Operator-facing description.
   - `is_acknowledged` (Boolean, indexed): Acknowledgment flag.
   - `created_at`: Incident timestamp.

---

## Redis Caching & Event Idempotency

- **Sub-millisecond Watchlist Lookup**:
  Active watchlist plates are pre-loaded into a Redis set (`watchlist:active_plates`). When a vehicle plate is recognized via OCR, the plate is normalized (`plate.upper().replace(' ', '').replace('-', '')`) and queried against Redis with `SISMEMBER` in sub-millisecond latency.
  *(Falls back gracefully to an in-memory thread-safe cache if Redis is offline during local runs).*
- **Event Idempotency Check**:
  Duplicate entry frames for the same camera and vehicle `track_id` on `POST /api/v1/ai-events` are detected using Redis (`SET NX EX`) within `IDEMPOTENCY_WINDOW_SECONDS` (10 seconds by default). Duplicate entry events return the existing session without creating duplicate database records.

---

## Authentication

Standard query endpoints are public. AI telemetry ingestion and camera-zone reads require a non-empty API key; missing or incorrect keys are rejected:
```http
x-api-key: dev-key
```
*(Configure the same `AI_API_KEY` in `backend/.env` and `ai-service/.env`. The `dev-key` default is for local development only.)*

---

## Core REST API Endpoints (/api/v1)

### POST /api/v1/ai-events
Ingests telemetry events from YOLOv8 tracking and EasyOCR plate recognition.

AI sends canonical snake_case fields and `event_type`; legacy `type`, `trackId`, `vehicleType`, `plate`, `slotId`, and `cameraId` aliases remain accepted.

**Event Types Supported:**
- `ENTRY`: Vehicle enters. Reserves a camera-scoped slot and creates an `ACTIVE` session. A later entry carrying an OCR plate updates that session and checks the watchlist.
- `plate` (legacy): OCR license plate detected. Normalizes plate, checks Redis watchlist; if matched, creates a `HIGH` severity `STOLEN_VEHICLE` alert immediately.
- `parked`: Vehicle parks in slot polygon. Updates session `actual_slot_id` and marks slot `OCCUPIED`.
- `exit`: Vehicle departs. Computes duration in minutes, sets session `COMPLETED`, frees parking slot.
- `ALERT` with `alert_type=WRONG_PARKING`: Vehicle parked outside designated polygons. Triggers `WRONG_PARKING` alert.
- `ALERT` with `alert_type=CRASH` or `ACCIDENT`: Collision detected and triggers an `ACCIDENT` alert.
- `stolen_vehicle`: Direct watchlist alert with snapshot.

**Request:**
```bash
curl -X POST http://localhost:5000/api/v1/ai-events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ENTRY",
    "track_id": 101,
    "vehicle_category": "COMPACT_CAR",
    "camera_id": "cam-1"
  }'
```

**Response (`201 Created`):**
```json
{
  "success": true,
  "event_type": "entry",
  "message": "Processed entry event",
  "session": {
    "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "track_id": 101,
    "plate_number": null,
    "vehicle_category": "COMPACT_CAR",
    "assigned_slot_id": "A-03",
    "actual_slot_id": null,
    "camera_id": "cam-1",
    "entry_time": "2026-11-16T22:30:00Z",
    "exit_time": null,
    "duration_minutes": 0.0,
    "status": "ACTIVE",
    "overstay_alerted": false
  },
  "allocation": {
    "recommended_slot_id": "A-03",
    "zone": "ZONE-A",
    "allowed_category": "COMPACT_CAR",
    "status": "RESERVED"
  }
}
```

---

### POST /api/v1/slots/allocate
Smart slot allocation reserves an available camera-scoped slot matching the vehicle category, with automatic fallback hierarchy. It selects by polygon-centroid distance when a camera-frame `reference_point` is supplied; without one it uses deterministic zone and slot-ID ordering.

**Fallback Hierarchy:**
- `TWO_WHEELER` -> `COMPACT_CAR` -> `SUV_SEDAN`
- `COMPACT_CAR` -> `SUV_SEDAN` -> `HEAVY_VEHICLE`
- `SUV_SEDAN` -> `HEAVY_VEHICLE`
- `HEAVY_VEHICLE` -> None

**Request:**
```bash
curl -X POST http://localhost:5000/api/v1/slots/allocate \
  -H "Content-Type: application/json" \
  -d '{"vehicle_category":"TWO_WHEELER","camera_id":"cam-1","reference_point":[120,220]}'
```

**Response (`200 OK`):**
```json
{
  "recommended_slot_id": "A-01",
  "camera_id": "cam-1",
  "zone": "ZONE-A",
  "allowed_category": "TWO_WHEELER",
  "status": "RESERVED",
  "message": "Slot A-01 (ZONE-A) allocated successfully."
}
```

---

### Parking Slots CRUD (/api/v1/slots)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/slots` | List slots with optional filters (`camera_id`, `zone`, `status`, `allowed_category`); `configured_only=true` limits results to slots with camera polygons. |
| `POST` | `/api/v1/slots` | Create / configure slot with camera ID and polygon coordinates. |
| `GET` | `/api/v1/slots/{slot_id}` | Retrieve specific slot details. |
| `PATCH` | `/api/v1/slots/{slot_id}` | Update camera ID, status, polygon coordinates, or assigned category. |
| `DELETE` | `/api/v1/slots/{slot_id}` | Delete parking slot. |

---

### Camera Zones

`GET /api/v1/cameras/{camera_id}/zones` requires `x-api-key` and returns that camera's persisted slot polygons and vehicle categories. It currently returns empty `no_parking_zones` and `tripwires` arrays because the backend does not persist those zone types. Use `backend/scripts/sync_camera_zones.py` to synchronize polygons from `ai-service/config/slots.json`; it clears stale polygons for that camera but preserves the slot records. Restart the AI service after syncing because camera workers load their zone map at startup. Coordinates are `[x, y]` points in that camera's pixel space.

---

### Plate OCR (`POST /api/v1/ocr/plate`)

The dashboard uploads a single photo to the backend, which forwards it in memory to the local AI service at `AI_SERVICE_URL`. The AI-service endpoint requires the configured `AI_API_KEY`; the browser never receives that service credential. The workflow does not save the image or OCR result. The current browser-facing backend follows the rest of the prototype API and does not authenticate dashboard users, so expose it only to trusted networks.

Supported formats are JPEG, PNG, WebP, and BMP, up to 10 MB. The AI service validates the image signature, decodes it, checks its dimensions, then runs local EasyOCR. Provide a close, sharp image with the full plate visible. If `PLATE_MODEL` is unset, OCR reads text from the image rather than using a trained plate-localization model, so a tightly cropped plate photo is recommended.

Response:

```json
{
  "success": true,
  "plate_detected": true,
  "text": "RJ14 AB 1234",
  "raw_text": "RJ14 AB 1234",
  "normalized_text": "RJ14AB1234",
  "confidence": 0.92,
  "is_low_confidence": false,
  "candidates": [{"text": "RJ14 AB 1234", "confidence": 0.92}],
  "error": null
}
```

`text`/`raw_text` preserve OCR output; `normalized_text` is a format-based suggestion, not a verified identity. `plate_detected` means the recognized text matched a supported plate pattern, not that ownership or identity was verified. When no plate-like text can be confirmed, the endpoint still returns a structured result with `plate_detected: false`, candidate text if any, and an explanatory `error`. Human review is required, especially for low-confidence results. The endpoint returns `413` for oversized files, `415` for unsupported image formats, `503` if local OCR weights are unavailable, and `504` if the AI service times out.

The backend's `AI_SERVICE_URL` defaults to `http://127.0.0.1:8001`; set the same `AI_API_KEY` in `backend/.env` and `ai-service/.env`. Example:

```powershell
curl.exe -F "file=@C:\path\to\plate.jpg" http://localhost:5000/api/v1/ocr/plate
```

---

### Vehicle Sessions History & Filters (/api/v1/sessions)

**Query Parameters:**
- `plate` (string): Search plate number (partial match).
- `status` (string): `ACTIVE`, `COMPLETED`, `OVERSTAY`.
- `vehicle_category` (string): Filter by category.
- `page` (integer, default: 1): Page number.
- `limit` (integer, default: 20): Items per page.

**Response Headers:**
```http
X-Total-Count: 15
Access-Control-Expose-Headers: X-Total-Count
```

**Request:**
```bash
curl -i "http://localhost:5000/api/v1/sessions?plate=RJ14&status=COMPLETED&page=1&limit=20"
```

---

### Watchlist Management (/api/v1/watchlist)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/watchlist` | List registered watchlist plates (filtered by `is_active`, `search`). |
| `POST` | `/api/v1/watchlist` | Add license plate to watchlist (normalizes and updates Redis cache). |
| `GET` | `/api/v1/watchlist/{id}` | Get single watchlist entry. |
| `PUT` | `/api/v1/watchlist/{id}` | Update reason or active status. |
| `DELETE` | `/api/v1/watchlist/{id}` | Remove license plate from watchlist and Redis cache. |

---

### Alerts & Acknowledgment (/api/v1/alerts)

**Query Parameters:**
- `type` (string): `STOLEN_VEHICLE`, `ACCIDENT`, `WRONG_PARKING`, `OVERSTAY`.
- `severity` (string): `HIGH`, `MEDIUM`, `LOW`.
- `acknowledged` (boolean): `true` or `false`.
- `plate` (string): Filter by plate number.
- `page` (int), `limit` (int): Pagination controls.

**Acknowledge Alert:**
```bash
curl -X PATCH http://localhost:5000/api/v1/alerts/{alert_id}/ack
```

---

## Real-Time WebSocket (/ws/events)

Connect to `ws://localhost:5000/ws/events`. Messages use `{ "event": "...", "data": ... }` and are broadcast in real time:

```json
{
  "event": "alert:new",
  "data": {
    "alert_id": "c1f7a4e2-...",
    "alert_type": "STOLEN_VEHICLE",
    "severity": "HIGH",
    "plate_number": "RJ14AB1234",
    "camera_id": "cam-1",
    "snapshot_url": "/media/alerts/example.jpg",
    "message": "CRITICAL: Stolen vehicle detected on camera cam-1: RJ14AB1234 (Reason: STOLEN)",
    "is_acknowledged": false,
    "created_at": "2026-11-16T22:30:00Z"
  }
}
```

### Supported Broadcast Events:
| Event Name | Direction | Payload | Description |
|---|---|---|---|
| `alert:new` | Server -> Client | `Alert` object | Emitted whenever a safety alert (accident, stolen vehicle, wrong parking, overstay) is triggered. |
| `alert:ack` | Server -> Client | `Alert` object | Emitted when an operator acknowledges an alert. |
| `session:new` | Server -> Client | `ParkingSession` object | Emitted when a vehicle enters the facility. |
| `session:update` | Server -> Client | `ParkingSession` object | Emitted when a session's plate, slot, or exit duration is updated. |
| `slots:update` | Server -> Client | Array of `ParkingSlot` objects | Emitted when parking slot occupancy changes (`AVAILABLE` <-> `OCCUPIED` / `RESERVED`). |

---

## Duration & Overstay Background Worker

- **Calculation on Exit**: When an `exit` event arrives, duration is computed in exact minutes: `duration_minutes = (exit_time - entry_time).total_seconds() / 60.0`.
- **Periodic Background Check**: Runs automatically every 60 seconds (configurable via `OVERSTAY_CHECK_INTERVAL_SECONDS`). Any `ACTIVE` session exceeding `MAX_ALLOWED_DURATION` (default: 240 mins / 4 hours) is marked `status = OVERSTAY`, an `OVERSTAY` alert is generated, and broadcast via WebSocket to the security dashboard.

---

## Legacy Frontend Compatibility Endpoints (/api)

The `/api/...` compatibility routes remain available to older clients. The current TypeScript dashboard uses the `/api/v1/...` routes as its primary API.

### GET /api/health
```json
{
  "ok": true,
  "database": "sqlite-fallback",
  "time": "2026-11-15T14:30:00.000Z"
}
```

### GET /api/v1/stats and GET /api/stats
Returns all-time alert totals, open/today alert counts, active sessions (including overstay), and capacity/availability for camera-mapped slots only. `availableByCategory` contains free mapped slots by vehicle category; unconfigured database rows are excluded. The optional `timezone_offset_minutes` query parameter (minutes west of UTC, as returned by JavaScript `Date.getTimezoneOffset()`) scopes “today” counts to the dashboard's local date.
```json
{
  "totalCapacity": 12,
  "totalSlots": 12,
  "availableSlots": 7,
  "availableByCategory": {
    "TWO_WHEELER": 2,
    "COMPACT_CAR": 3,
    "SUV_SEDAN": 2,
    "HEAVY_VEHICLE": 0
  },
  "occupiedSlots": 5,
  "reservedSlots": 0,
  "activeVehicles": 5,
  "totalAlerts": 8,
  "alertsToday": 3,
  "todayEntries": 24,
  "openAlerts": 2
}
```

### GET /api/analytics/hourly
Calculates hourly vehicle entry distribution for a given date (`date=YYYY-MM-DD`, `nonzero=true`).

### GET /api/slots
Returns all configured parking slots and their current allocation status.

### GET /api/slots/recommend
Recommends the best available parking slot based on vehicle class (`type=bike|car|suv|heavy_vehicle`).

### GET /api/sessions
Retrieves parking sessions with pagination and search filters (`plate`, `status`, `page`, `limit`).
Returns `X-Total-Count` header.

### GET /api/alerts & PATCH /api/alerts/:id/ack
Filter by `type`, `acknowledged`, `severity`, `page`, `limit`. Returns `X-Total-Count` header. Acknowledge via `PATCH /api/alerts/:id/ack`.

### Watchlist Legacy (/api/watchlist)
`GET /api/watchlist`, `POST /api/watchlist`, `DELETE /api/watchlist/:id`.

### Event Ingestion Legacy (/api/events)
Requires `x-api-key` and accepts legacy `type`, `trackId`, and `vehicleType` aliases with `snapshot` base64 images.

---

## Static Media Storage (/uploads)

When events include a `snapshot` (base64 image), the backend decodes and stores it under `backend/uploads/` and records `/uploads/<filename>`. AI-generated `snapshot_url` files are served from the AI service's `/media/alerts` static route.
