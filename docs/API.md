# API Reference Documentation

Smart CCTV Parking & Vehicle Safety System Backend REST API and Real-Time Telemetry Interface.

- **Base URL**: `http://localhost:5000`
- **Default Port**: `5000`
- **Content-Type**: `application/json`
- **Max JSON Payload**: `10MB` (accommodates base64 snapshot uploads)

---

## Table of Contents
1. [Authentication](#authentication)
2. [Pagination & Filtering Standard](#pagination--filtering-standard)
3. [Static Media Storage](#static-media-storage)
4. [Overview & Analytics](#overview--analytics)
   - [GET /api/health](#get-apihealth)
   - [GET /api/stats](#get-apistats)
   - [GET /api/analytics/hourly](#get-apianalyticshourly)
5. [Parking Slots](#parking-slots)
   - [GET /api/slots](#get-apislots)
   - [GET /api/slots/recommend](#get-apislotsrecommend)
6. [Parking Sessions](#parking-sessions)
   - [GET /api/sessions](#get-apisessions)
7. [Alerts & Safety Incidents](#alerts--safety-incidents)
   - [GET /api/alerts](#get-apialerts)
   - [PATCH /api/alerts/:id/ack](#patch-apialertsidack)
8. [Watchlist (Stolen / Wanted Vehicles)](#watchlist-stolen--wanted-vehicles)
   - [GET /api/watchlist](#get-apiwatchlist)
   - [POST /api/watchlist](#post-apiwatchlist)
   - [DELETE /api/watchlist/:id](#delete-apiwatchlistid)
9. [Event Ingestion (AI Service / Edge Cams)](#event-ingestion-ai-service--edge-cams)
   - [POST /api/events](#post-apievents)
10. [Static Files](#static-files)
    - [GET /uploads/:filename](#get-uploadsfilename)
11. [Versioned AI Events](#versioned-ai-events)
12. [Camera Zones](#camera-zones)
13. [WebSocket Events](#websocket-events)

---

## Authentication

All standard queries are public.

AI event ingestion and camera-zone endpoints require an API key in the request header:
```http
x-api-key: dev-key
```
*(Configure `AI_API_KEY` in `backend/.env`, defaults to `dev-key` in development).*

---

## Pagination & Filtering Standard

Endpoints returning collections (`/api/sessions`, `/api/alerts`) return a standard JSON Array `[...]` for compatibility with existing UI components, while exposing pagination metadata via HTTP response headers:

- `X-Total-Count`: Total number of records matching the filter criteria.
- `Access-Control-Expose-Headers`: Exposes `X-Total-Count` for cross-origin browser clients.

### Common Pagination Query Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | Integer | `1` | 1-based page index. |
| `limit` | Integer | `20` (or 100/200 when unpaginated) | Maximum items to return per page. |

---

## Static Media Storage

When crash or stolen vehicle events are received with a `snapshot` (base64 image), the server decodes the image, stores it on disk under `backend/uploads/snap-<timestamp>-<hash>.jpg`, and records the relative URL `/uploads/<filename>` in the alert document. Images are served statically via Express.

Snapshots generated directly by the AI service are saved under its configured `EVENT_SNAPSHOT_DIR`
and exposed at `/media/alerts/:filename`. The frontend development proxy forwards this path to the
AI service; deployments should route the same path to the AI service or shared media storage.

---

## Overview & Analytics

### GET /api/health
Checks backend operational status and current server timestamp.

**Request:**
```bash
curl -X GET http://localhost:5000/api/health
```

**Response (`200 OK`):**
```json
{
  "ok": true,
  "time": "2026-11-15T14:30:00.000Z"
}
```

---

### GET /api/stats
Returns aggregate parking occupancy, vehicle count, daily entries, and open security alerts.

**Request:**
```bash
curl -X GET http://localhost:5000/api/stats
```

**Response (`200 OK`):**
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

---

### GET /api/analytics/hourly
Calculates hourly vehicle entry distribution for a given date.

**Query Parameters:**
- `date` *(optional)*: Target date `YYYY-MM-DD` (defaults to today).
- `nonzero` *(optional)*: `true` to return only hours with entries > 0.

**Request:**
```bash
curl -X GET "http://localhost:5000/api/analytics/hourly?date=2026-11-15&nonzero=true"
```

**Response (`200 OK`):**
```json
[
  { "hour": 9, "entries": 4 },
  { "hour": 10, "entries": 8 },
  { "hour": 11, "entries": 12 }
]
```

---

## Parking Slots

### GET /api/slots
Returns all configured parking slots and their current allocation status.

**Request:**
```bash
curl -X GET http://localhost:5000/api/slots
```

**Response (`200 OK`):**
```json
[
  {
    "_id": "67053e1a00a1b2c3d4e5f601",
    "slotId": "A-01",
    "type": "bike",
    "status": "free",
    "currentSession": null,
    "createdAt": "2026-10-08T10:00:00.000Z",
    "updatedAt": "2026-10-08T10:00:00.000Z"
  },
  {
    "_id": "67053e1a00a1b2c3d4e5f602",
    "slotId": "A-02",
    "type": "car",
    "status": "occupied",
    "currentSession": "67053f2200a1b2c3d4e5f603",
    "createdAt": "2026-10-08T10:00:00.000Z",
    "updatedAt": "2026-10-08T10:05:00.000Z"
  }
]
```

---

### GET /api/slots/recommend
Recommends the best available parking slot based on vehicle class (`bike`, `car`, `suv`, `heavy_vehicle`).

**Query Parameters:**
- `type` / `vehicleType`: Vehicle class (`bike` | `car` | `suv` | `heavy_vehicle`, default: `car`).
- `slotIds`: Optional comma-separated slot IDs to limit recommendations to spaces mapped by the active camera.

**Request:**
```bash
curl -X GET "http://localhost:5000/api/slots/recommend?type=car&slotIds=A-04,A-05"
```

**Response (`200 OK`):**
```json
{
  "slot": {
    "_id": "67053e1a00a1b2c3d4e5f604",
    "slotId": "A-04",
    "type": "car",
    "status": "free",
    "currentSession": null
  }
}
```

*(If no suitable slot is free, `"slot": null` is returned).*

---

## Parking Sessions

### GET /api/sessions
Retrieves parking sessions with pagination and search filters.

**Query Parameters:**
| Parameter | Type | Example | Description |
|---|---|---|---|
| `plate` | String | `RJ14` | Substring match (case-insensitive). |
| `status` | String | `closed` | Filter by status (`active` or `closed`). |
| `vehicleType` | String | `car` | Filter by vehicle type (`bike`, `car`, `suv`). |
| `slotId` | String | `A-04` | Filter by assigned slot. |
| `cameraId` | String | `cam-1` | Filter by detection camera. |
| `page` | Integer | `1` | Page number (default: 1). |
| `limit` | Integer | `20` | Results per page (default: 20). |

**Response Headers:**
```http
X-Total-Count: 45
Access-Control-Expose-Headers: X-Total-Count
```

**Request:**
```bash
curl -i -X GET "http://localhost:5000/api/sessions?plate=RJ14&status=closed&page=1&limit=20"
```

**Response (`200 OK`):**
```json
[
  {
    "_id": "67054a1a00a1b2c3d4e5f701",
    "trackId": 101,
    "cameraId": "cam-1",
    "plate": "RJ14-AB-1234",
    "vehicleType": "car",
    "slotId": "A-04",
    "entryTime": "2026-11-15T09:15:00.000Z",
    "exitTime": "2026-11-15T11:45:00.000Z",
    "durationSec": 9000,
    "status": "closed",
    "overstayAlerted": false,
    "createdAt": "2026-11-15T09:15:00.000Z",
    "updatedAt": "2026-11-15T11:45:00.000Z"
  }
]
```

---

## Alerts & Safety Incidents

### GET /api/alerts
Retrieves security, safety, and violation alerts with filters and pagination.

**Query Parameters:**
| Parameter | Type | Example | Description |
|---|---|---|---|
| `type` | String | `crash` | Alert category (`crash`, `stolen_vehicle`, `wrong_parking`, `overstay`). |
| `acknowledged` | Boolean | `false` | Filter by acknowledgment state (`true` or `false`). |
| `severity` | String | `high` | Filter by severity (`low`, `medium`, `high`). |
| `plate` | String | `RJ14` | Substring match on vehicle license plate. |
| `slotId` | String | `A-01` | Filter by slot ID. |
| `cameraId` | String | `cam-1` | Filter by camera ID. |
| `page` | Integer | `1` | Page number (default: 1). |
| `limit` | Integer | `20` | Results per page (default: 20). |

**Response Headers:**
```http
X-Total-Count: 8
Access-Control-Expose-Headers: X-Total-Count
```

**Request:**
```bash
curl -i -X GET "http://localhost:5000/api/alerts?type=crash&acknowledged=false&page=1&limit=20"
```

**Response (`200 OK`):**
```json
[
  {
    "_id": "67055c1a00a1b2c3d4e5f801",
    "type": "crash",
    "severity": "high",
    "plate": null,
    "cameraId": "cam-1",
    "slotId": null,
    "message": "Possible collision detected in aisle B",
    "snapshot": "/uploads/snap-1731681234567-a1b2c3d4.jpg",
    "acknowledged": false,
    "createdAt": "2026-11-15T14:10:00.000Z",
    "updatedAt": "2026-11-15T14:10:00.000Z"
  }
]
```

---

### PATCH /api/alerts/:id/ack
Acknowledges and clears an alert.

**Request:**
```bash
curl -X PATCH http://localhost:5000/api/alerts/67055c1a00a1b2c3d4e5f801/ack
```

**Response (`200 OK`):**
```json
{
  "_id": "67055c1a00a1b2c3d4e5f801",
  "type": "crash",
  "severity": "high",
  "acknowledged": true,
  "snapshot": "/uploads/snap-1731681234567-a1b2c3d4.jpg",
  "updatedAt": "2026-11-15T14:12:00.000Z"
}
```

---

## Watchlist (Stolen / Wanted Vehicles)

### GET /api/watchlist
Returns all registered watchlist vehicles.

**Request:**
```bash
curl -X GET http://localhost:5000/api/watchlist
```

**Response (`200 OK`):**
```json
[
  {
    "_id": "67052a1a00a1b2c3d4e5f901",
    "plate": "RJ14AB1234",
    "reason": "Stolen car report FIR #102/24",
    "active": true,
    "createdAt": "2026-10-08T09:00:00.000Z"
  }
]
```

---

### POST /api/watchlist
Adds a new license plate to the watchlist.

**Request Body:**
```json
{
  "plate": "DL01XY9999",
  "reason": "Wanted in traffic violation case",
  "active": true
}
```

**Request:**
```bash
curl -X POST http://localhost:5000/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"plate":"DL01XY9999","reason":"Wanted in traffic violation case"}'
```

**Response (`201 Created`):**
```json
{
  "_id": "67056b2a00a1b2c3d4e5f902",
  "plate": "DL01XY9999",
  "reason": "Wanted in traffic violation case",
  "active": true,
  "createdAt": "2026-11-15T14:20:00.000Z"
}
```

---

### DELETE /api/watchlist/:id
Removes an entry from the watchlist.

**Request:**
```bash
curl -X DELETE http://localhost:5000/api/watchlist/67056b2a00a1b2c3d4e5f902
```

**Response:**
`204 No Content`

---

## Event Ingestion (AI Service / Edge Cams)

### POST /api/events
Ingests telemetry events from YOLOv8 tracking and EasyOCR plate recognition.

**Headers:**
```http
Content-Type: application/json
x-api-key: dev-key
```

**Supported Event Types:**
- `entry`: Vehicle detected entering the parking lot.
- `plate`: OCR license plate confirmed for an active track.
- `parked`: Vehicle settled into a designated slot.
- `exit`: Vehicle left the parking area.
- `occupancy`: Reconciles the statuses of the slot IDs configured for this camera against current detections.
- `wrong_parking`: Vehicle stationary outside valid parking polygons.
- `crash`: Collision heuristic or ML detection triggered.
- `stolen_vehicle`: Watchlist match or stolen vehicle detected.

---

### Event Examples:

#### Camera occupancy reconciliation
The AI service sends the complete list of spaces in its camera map and the subset currently occupied.
For live sources, missing mapped spaces are registered and only those listed slots are synchronized;
other facility spaces are not changed. For prerecorded video, the backend broadcasts temporary
occupancy for the dashboard but does not save it to the database or create session/alert history.

```json
{
  "type": "occupancy",
  "cameraId": "cam-1",
  "sourceMode": "network",
  "detectionSummary": { "total": 3, "bikes": 1, "cars": 2 },
  "slots": [
    { "slotId": "A-04", "type": "car" },
    { "slotId": "A-05", "type": "car" },
    { "slotId": "A-06", "type": "car" }
  ],
  "occupiedSlotIds": ["A-05"]
}
```

`detectionSummary` is optional for older clients. When provided, its `total` must equal `bikes + cars`.
The counts represent tracked vehicles in the current processed frame, not unique arrivals or daily
totals. The COCO model groups SUVs with cars.

#### 1. Crash Event with Base64 Snapshot
When `snapshot` (base64 string or data URI) is provided, the backend writes the image to `backend/uploads/` and links the URL `/uploads/snap-...jpg` in the generated Alert document.

**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "crash",
    "cameraId": "cam-1",
    "trackIds": [12, 34],
    "message": "Sudden deceleration and bounding box overlap detected near aisle junction",
    "snapshot": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
  }'
```

**Response (`201 Created`):**
```json
{
  "alert": {
    "_id": "67057d3a00a1b2c3d4e5fa01",
    "type": "crash",
    "severity": "high",
    "plate": null,
    "trackIds": [12, 34],
    "cameraId": "cam-1",
    "slotId": null,
    "message": "Sudden deceleration and bounding box overlap detected near aisle junction",
    "snapshot": "/uploads/snap-1731682345678-b2c3d4e5.jpg",
    "acknowledged": false,
    "createdAt": "2026-11-15T14:25:00.000Z",
    "updatedAt": "2026-11-15T14:25:00.000Z"
  }
}
```

---

#### 2. Stolen Vehicle Event with Base64 Snapshot
**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "stolen_vehicle",
    "plate": "RJ14AB1234",
    "cameraId": "cam-1",
    "message": "Watchlist match: RJ14AB1234 flagged stolen",
    "snapshot": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
  }'
```

**Response (`201 Created`):**
```json
{
  "alert": {
    "_id": "67057d3a00a1b2c3d4e5fa02",
    "type": "stolen_vehicle",
    "severity": "high",
    "plate": "RJ14AB1234",
    "cameraId": "cam-1",
    "slotId": null,
    "message": "Watchlist match: RJ14AB1234 flagged stolen",
    "snapshot": "/uploads/snap-1731682345690-c3d4e5f6.jpg",
    "acknowledged": false,
    "createdAt": "2026-11-15T14:26:00.000Z",
    "updatedAt": "2026-11-15T14:26:00.000Z"
  }
}
```

---

#### 3. Vehicle Entry
**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "entry",
    "trackId": 201,
    "vehicleType": "car",
    "cameraId": "cam-1"
  }'
```

**Response (`201 Created`):**
```json
{
  "session": {
    "_id": "67057e0000a1b2c3d4e5fb01",
    "trackId": 201,
    "cameraId": "cam-1",
    "plate": null,
    "vehicleType": "car",
    "slotId": null,
    "entryTime": "2026-11-15T14:30:00.000Z",
    "status": "active",
    "overstayAlerted": false
  },
  "recommendedSlot": "A-04"
}
```

---

#### 4. OCR Plate Read Event
If the detected plate matches an active watchlist entry, a `stolen_vehicle` alert is automatically raised and broadcast via Socket.IO.

**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "plate",
    "trackId": 201,
    "plate": "RJ14-AB-1234",
    "snapshot": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }'
```

**Response (`201 Created`):**
```json
{
  "session": {
    "_id": "67057e0000a1b2c3d4e5fb01",
    "trackId": 201,
    "plate": "RJ14-AB-1234",
    "vehicleType": "car",
    "status": "active"
  }
}
```

---

#### 5. Vehicle Parked Event
**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "parked",
    "trackId": 201,
    "slotId": "A-04"
  }'
```

**Response (`201 Created`):**
```json
{
  "session": {
    "_id": "67057e0000a1b2c3d4e5fb01",
    "trackId": 201,
    "slotId": "A-04",
    "status": "active"
  }
}
```

---

#### 6. Vehicle Exit Event
Calculates duration and frees the slot.

**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "exit",
    "trackId": 201
  }'
```

**Response (`201 Created`):**
```json
{
  "session": {
    "_id": "67057e0000a1b2c3d4e5fb01",
    "trackId": 201,
    "status": "closed",
    "durationSec": 1845,
    "exitTime": "2026-11-15T15:00:45.000Z"
  }
}
```

---

#### 7. Wrong Parking Event
**Request:**
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "wrong_parking",
    "trackId": 202,
    "plate": "RJ14-CD-5678",
    "slotId": "A-01",
    "message": "Parked in aisle blocking emergency exit"
  }'
```

**Response (`201 Created`):**
```json
{
  "alert": {
    "_id": "67057e5000a1b2c3d4e5fc01",
    "type": "wrong_parking",
    "severity": "medium",
    "plate": "RJ14-CD-5678",
    "slotId": "A-01",
    "message": "Parked in aisle blocking emergency exit",
    "acknowledged": false
  }
}
```

---

## Static Files

### GET /uploads/:filename
Serves stored snapshot images recorded during crash or stolen vehicle incidents.

**Request:**
```bash
curl -X GET http://localhost:5000/uploads/snap-1731682345678-b2c3d4e5.jpg --output snapshot.jpg
```
Or open directly in any web browser:
```
http://localhost:5000/uploads/snap-1731682345678-b2c3d4e5.jpg
```

**Response (`200 OK`):**
- Headers: `Content-Type: image/jpeg`
- Body: Binary image file.

---

## Versioned AI Events

`POST /api/v1/ai-events` accepts canonical event IDs, ISO timestamps, camera and tracking IDs,
vehicle categories, plate data, slot IDs, event types, alert types, and snapshot paths. The endpoint
validates the payload, maps it to the existing session and alert logic, and deduplicates event IDs
for seven days. The original `/api/events` endpoint remains available for dashboard occupancy
updates and older AI clients.

## Camera Zones

`GET /api/v1/cameras/:cameraId/zones` returns slot polygons stored on parking-slot records, along
with that camera's optional no-parking polygons and entry/exit tripwires. `PUT` accepts any subset
of `slots`, `no_parking_zones`, and `tripwires`; slot geometry is upserted without deleting other
slots. Coordinates are `[x,y]` points in the source camera's pixel space. The AI service fetches
this configuration when each worker starts.

## WebSocket Events

Connect to `/ws/events` for JSON messages shaped as `{ "event": "alert:new", "payload": ... }`.
The connection also receives an initial `connected` message. The backend continues to emit the
same events via Socket.IO for older dashboard clients.

Clients connect to the Socket.IO server at `/` (same port as HTTP server, e.g. `http://localhost:5000`).

| Event Name | Direction | Payload | Description |
|---|---|---|---|
| `alert:new` | Server -> Client | `Alert` object | Emitted whenever a safety alert (crash, stolen vehicle, wrong parking, overstay) is triggered. |
| `session:new` | Server -> Client | `ParkingSession` object | Emitted when a vehicle enters the parking facility. |
| `session:update` | Server -> Client | `ParkingSession` object | Emitted when a session's plate, slot, or exit duration is updated. |
| `slots:update` | Server -> Client | Array of `ParkingSlot` objects | Emitted when parking slot occupancy changes (`free` <-> `occupied`). |

The same event names and payloads are sent as JSON messages on the native WebSocket endpoint
`/ws/events`; Socket.IO is retained for compatibility.
