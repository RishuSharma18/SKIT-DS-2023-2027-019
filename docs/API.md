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

## Database Schema (PostgreSQL) & Migrations

The database schema is managed via **Alembic** migrations (`backend/alembic/`):
```bash
cd backend
alembic upgrade head
python scripts/seed.py
```

### Table Definitions:
1. **`parking_slots`**:
   - `slot_id` (String PK): Unique slot identifier (e.g. `A-01`, `B-03`).
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
   - `snapshot_url` (String, nullable): Local URL to saved evidence image (`/uploads/snap-...jpg`).
   - `message` (String): Operator-facing description.
   - `is_acknowledged` (Boolean, indexed): Acknowledgment flag.
   - `created_at`: Incident timestamp.

---

## Redis Caching & Event Idempotency

- **Sub-millisecond Watchlist Lookup**:
  Active watchlist plates are pre-loaded into a Redis set (`watchlist:active_plates`). When a vehicle plate is recognized via OCR, the plate is normalized (`plate.upper().replace(' ', '').replace('-', '')`) and queried against Redis with `SISMEMBER` in sub-millisecond latency.
  *(Falls back gracefully to an in-memory thread-safe cache if Redis is offline during local runs).*
- **Event Idempotency Check**:
  Duplicate video frames for the same vehicle `track_id` on `POST /api/v1/ai-events` (within a configurable 10-second deduplication window) are detected using Redis key `event:entry:{track_id}` (`SET NX EX 10`). Duplicate entry events return the existing session without creating duplicate database records.

---

## Authentication

All standard query endpoints are public. AI telemetry ingestion and camera zone updates accept an API key in the request header:
```http
x-api-key: dev-key
```
*(Configured via `AI_API_KEY` in `backend/.env`).*

---

## Core REST API Endpoints (/api/v1)

### POST /api/v1/ai-events
Ingests telemetry events from YOLOv8 tracking and EasyOCR plate recognition.

**Event Types Supported:**
- `entry`: Vehicle enters parking area. Triggers smart slot allocation, reserves slot, creates `ACTIVE` vehicle session.
- `plate`: OCR license plate detected. Normalizes plate, checks Redis watchlist; if matched, creates `HIGH` severity `STOLEN_VEHICLE` alert immediately.
- `parked`: Vehicle parks in slot polygon. Updates session `actual_slot_id` and marks slot `OCCUPIED`.
- `exit`: Vehicle departs. Computes duration in minutes, sets session `COMPLETED`, frees parking slot.
- `wrong_parking`: Vehicle parked outside designated polygons. Triggers `WRONG_PARKING` alert.
- `crash` / `accident`: Collision detected. Saves base64 snapshot to disk, triggers `ACCIDENT` alert.
- `stolen_vehicle`: Direct watchlist alert with snapshot.

**Request:**
```bash
curl -X POST http://localhost:5000/api/v1/ai-events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "entry",
    "trackId": 101,
    "vehicleType": "COMPACT_CAR",
    "cameraId": "cam-1"
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
Smart slot allocation engine finding the nearest `AVAILABLE` slot matching the vehicle category, with automatic fallback hierarchy.

**Fallback Hierarchy:**
- `TWO_WHEELER` -> `COMPACT_CAR` -> `SUV_SEDAN`
- `COMPACT_CAR` -> `SUV_SEDAN` -> `HEAVY_VEHICLE`
- `SUV_SEDAN` -> `HEAVY_VEHICLE`
- `HEAVY_VEHICLE` -> None

**Request:**
```bash
curl -X POST http://localhost:5000/api/v1/slots/allocate \
  -H "Content-Type: application/json" \
  -d '{"vehicle_category":"TWO_WHEELER"}'
```

**Response (`200 OK`):**
```json
{
  "recommended_slot_id": "A-01",
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
| `GET` | `/api/v1/slots` | List all slots with optional filters (`zone`, `status`, `allowed_category`). |
| `POST` | `/api/v1/slots` | Create / configure slot with polygon coordinates. |
| `GET` | `/api/v1/slots/{slot_id}` | Retrieve specific slot details. |
| `PATCH` | `/api/v1/slots/{slot_id}` | Update status, polygon coordinates, or assigned category. |
| `DELETE` | `/api/v1/slots/{slot_id}` | Delete parking slot. |

---

### Camera Zones

`GET /api/v1/cameras/:cameraId/zones` returns slot polygons stored on parking-slot records, along with that camera's optional no-parking polygons and entry/exit tripwires. `PUT` accepts any subset of `slots`, `no_parking_zones`, and `tripwires`; slot geometry is upserted without deleting other slots. Coordinates are `[x,y]` points in the source camera's pixel space.

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

Connect to `ws://localhost:5000/ws/events`. All dashboard updates and security notifications are broadcast in real-time JSON format:

```json
{
  "event": "alert:new",
  "data": {
    "alert_id": "c1f7a4e2-...",
    "alert_type": "STOLEN_VEHICLE",
    "severity": "HIGH",
    "plate_number": "RJ14AB1234",
    "camera_id": "cam-1",
    "snapshot_url": "/uploads/snap-1731682345678-b2c3d4e5.jpg",
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

The existing React dashboard endpoints (`/api/slots`, `/api/sessions`, `/api/alerts`, `/api/stats`, `/api/health`, `/api/slots/recommend`, `/api/analytics/hourly`) are fully mapped and compatible without any frontend breaking changes.

### GET /api/health
```json
{
  "ok": true,
  "time": "2026-11-15T14:30:00.000Z"
}
```

### GET /api/stats
```json
{
  "totalSlots": 12,
  "freeSlots": 7,
  "occupied": 5,
  "occupiedSlots": 5,
  "activeVehicles": 5,
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
Accepts legacy and occupancy payloads (`type: occupancy`, `type: crash`, etc.) with `snapshot` base64 images.

---

## Static Media Storage (/uploads)

When crash, accident, or stolen vehicle events are received with a `snapshot` (base64 image), the server decodes the image, stores it on disk under `backend/uploads/snap-<timestamp>-<hash>.jpg`, and records the relative URL `/uploads/<filename>` in the alert document. Images are served statically from `/uploads`.
