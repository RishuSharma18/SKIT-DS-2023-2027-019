# AI-Powered Smart CCTV Parking & Vehicle Safety System

Final-year B.Tech project, CSE (Data Science), SKIT Jaipur, batch 2023-27. Guide: Dr. Nilam Chaudhary.

CCTV video → **AI service** (YOLOv8 + EasyOCR) → **Backend** (FastAPI + PostgreSQL/SQLite + Redis) → **Dashboard** (React).
The active backend is `backend/app` (FastAPI). `backend/src` and its npm scripts are legacy Express/MongoDB code and are not used by the current dashboard or AI service.

```
 ┌──────────┐  frames  ┌─────────────────┐  REST events  ┌────────────────┐  WebSocket   ┌───────────────┐
 │ CCTV /   │ ───────► │  ai-service     │ ────────────► │  backend       │ ──────────► │  frontend     │
 │ video    │          │  Python+FastAPI │  x-api-key    │  Python+FastAPI│  + REST     │  React (Vite) │
 └──────────┘          │  YOLOv8,OpenCV, │               │  PostgreSQL   │             │  dashboard    │
                       │  EasyOCR        │               │  + Redis      │             └───────────────┘
                       └─────────────────┘
```

## Folder structure
| Folder | Owner | What lives here |
|---|---|---|
| `ai-service/` | Rishu (detection), Nandani (OCR) | Multi-camera ingestion, detection/tracking, OCR, zone rules |
| `backend/app/` | Vaibhav | Active FastAPI API, SQLAlchemy models, event handling, alerts, WebSockets |
| `backend/src/` | Legacy | Historical Express/MongoDB implementation; not part of the active run path |
| `frontend/` | Bhumi | React dashboard |
| `docs/` | everyone | Plan, Git workflow, report material |

## Quick start (first time)
Prereqs: Node 18+, Python 3.10+, and PostgreSQL/Redis (Docker Compose is optional; the backend can use its SQLite/in-memory development fallbacks).

Start PostgreSQL and Redis if using Docker:

```powershell
docker compose up -d postgres redis
```

Start the backend in Terminal 1:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Set the same non-default AI_API_KEY in backend/.env and ai-service/.env before integration.
# Without PostgreSQL, set DATABASE_URL=sqlite:///./cctv_parking.db in backend/.env before migrations.
alembic upgrade head
# If upgrading a pre-Alembic SQLite database created by an older app version, run this once instead:
# alembic stamp 001_initial_schema
# alembic upgrade head
python scripts\seed.py
# Optional: replace the seed polygons with the current AI-service camera map.
python scripts\sync_camera_zones.py --camera-id cam-1
python -m uvicorn app.main:app --host 127.0.0.1 --port 5000 --reload
```

Start the frontend in Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Set up the AI service in Terminal 3:

```powershell
cd ai-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
New-Item -ItemType Directory -Force samples | Out-Null
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Set BACKEND_URL=http://localhost:5000 and the matching AI_API_KEY in ai-service/.env.
# Put a camera video at samples\parking.mp4 and draw its polygons if needed:
# python tools\draw_slots.py --source samples\parking.mp4 --out config\slots.json
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The backend defaults to SQLite and in-memory caching when PostgreSQL/Redis are unavailable.
The health endpoint reports the active storage (`sqlite-fallback` when applicable). Do not use
the default `dev-key` in a deployed environment; set the same strong `AI_API_KEY` in both services.
Apply Alembic migrations before starting against an existing database.
If an older app already created the SQLite tables before Alembic was introduced, record that
matching schema with `alembic stamp 001_initial_schema` once, then run `alembic upgrade head`;
this preserves existing rows while applying newer migrations. Do not stamp a fresh database.

The sample `ai-service/config/slots.json` maps five open compact-car bays in the top row of the
included sample video's frame 30 (3840x2160); it is only suitable for that same fixed camera and
frame geometry, not a confirmed physical facility. The dashboard capacity and category counts only
include slots with configured polygons; active vehicles include active and overstay sessions, and
the alert KPI is the all-time total with open and local-today counts beneath it. The dashboard
identifies prerecorded input as video replay and hides live counts and recommendations until a
webcam or network camera and matching spaces are configured. It only displays the spaces mapped by
the active camera; occupancy is refreshed from detections in those bays. For live cameras, set
`RTSP_URLS` in `ai-service/.env` to a JSON object or comma-separated
`CAMERA_ID=RTSP_URL` pairs. Each camera has an independent reconnecting reader, tracker, and
analytics worker; inspect their state at `/health` and their video at `/video_feed/{camera_id}`.
The dashboard feed uses the primary configured camera. Slot polygons are fetched from the backend's
`/api/v1/cameras/{camera_id}/zones` endpoint. `backend/scripts/sync_camera_zones.py` upserts the selected camera's configured polygons and clears
stale polygons for that camera without deleting its slots or touching other cameras. The current backend
stores slot polygons; its zone response leaves `no_parking_zones` and `tripwires` empty until those
zone types are added to backend storage. Sample-video occupancy is broadcast as a temporary estimate and is not saved,
and replay-generated sessions and alerts are disabled.
YOLO's COCO classes include motorcycle and car (SUVs are included in car); COCO cannot reliably
distinguish an SUV from another car. A separately trained classifier is needed for that distinction.
Entry/exit events are emitted when a tracked vehicle crosses a configured tripwire or enters/leaves a mapped bay. Disable OCR in
`.env` with `ENABLE_OCR=0` for detection-only runs when EasyOCR is not needed. Inference defaults
to 1280px and uses overlapping tiles for high-resolution sources to improve small-vehicle recall, at
a higher processing cost. Smaller sources use a single full-frame tile. CPU inference may not keep up
with a live stream; a supported GPU or lower `YOLO_IMAGE_SIZE` may be needed. The camera overlay
legend explains box/bay colors; blue boxes are detected vehicles, red boxes are confirmed in a mapped
bay, green bays are available, and red bays are occupied. Vehicle boxes also show the model confidence
score. In video replay mode, the dashboard reports the current tracked-frame total and bike/car counts;
COCO SUVs are included in cars. Detection counts and confidence are model estimates, not ground-truth
accuracy measurements; validate on annotated frames from the target camera. COCO bus and truck
classes map to `HEAVY_VEHICLE`; a separate custom model/class map is required to distinguish SUVs
from other cars.

### Number-plate OCR from a photo

Plate OCR is a separate dashboard workflow from CCTV vehicle detection. Open **Plate OCR**, choose
or drop a JPEG, PNG, WebP, or BMP photo (maximum 10MB), preview it, then explicitly select
**Recognize plate**. Results show the raw OCR text, a format-normalized suggestion, confidence, and
alternatives when available. Review every result against the image; a recognized string is not
identity verification. The photo is forwarded through the backend to the local AI service and is
processed in memory, not persisted.

The backend must be running with `AI_SERVICE_URL=http://127.0.0.1:8001`, and the backend and
AI-service `.env` files must have the same `AI_API_KEY`. The AI service requires local EasyOCR
English model weights in `ai-service/models/easyocr` by default (or configure
`EASYOCR_MODEL_DIR`). The OCR endpoint does not download weights at runtime; if the weights are
missing, it reports an actionable service error. For best recognition, upload a sharp, close-up
image with the full plate visible. With `PLATE_MODEL` unset, EasyOCR reads text from the submitted
image without a dedicated plate-localization model, so whole-vehicle photos may not yield a plate.
`PLATE_MODEL` can point to an existing local YOLO plate detector weight if available.
If the English EasyOCR files are missing, download them once using EasyOCR's model loader:

```powershell
cd ai-service
.\.venv\Scripts\python.exe -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='models/easyocr', download_enabled=True)"
```

The app itself keeps model downloading disabled. The browser-facing backend currently has no user
authentication, consistent with the rest of this prototype API; expose it only on a trusted network.

Example request (backend and AI service must both be running):

```powershell
curl.exe -F "file=@C:\path\to\plate.jpg" http://localhost:5000/api/v1/ocr/plate
```

Run the OCR service tests with `cd ai-service; python tests_plate.py`; the backend proxy and
upload-validation checks are included in `python tests/run_tests.py`.

### Test a crash alert end to end

The synthetic tests cover the detector and backend crash-event contract:

```bash
cd ai-service && python tests_crash.py
cd ai-service && python tests_vehicle.py && python tests_detection.py
cd ../backend && python tests/run_tests.py
```

With the backend running, submit a synthetic crash event to verify it appears in the dashboard Alerts panel:

```bash
curl -X POST localhost:5000/api/events -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"crash","trackIds":[12,34],"message":"Test collision between tracks 12 and 34"}'
```

The AI pipeline emits this alert automatically when its overlap-and-deceleration heuristic triggers. Crash alerts show both track IDs in the dashboard. Treat them as possible collisions until validated against real footage.

### Test the backend without any AI (fake an event)
```bash
curl -X POST localhost:5000/api/events -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"entry","trackId":1,"vehicleType":"car","plate":"RJ14AB1234"}'
```
A **stolen_vehicle** alert should appear on the dashboard (that plate is in the seeded watchlist).

## REST API Endpoints
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | None | Database health and active storage |
| `GET` | `/api/stats` | None | Overview metrics (total slots, free, occupied, active vehicles, today's entries, open alerts) |
| `GET` | `/api/analytics/hourly` | None | Today's parking entries grouped by hour |
| `GET` | `/api/slots` | None | List all parking slots and real-time statuses |
| `GET` | `/api/slots/recommend?vehicleType=car` | None | Legacy best available slot recommendation |
| `GET` | `/api/sessions` | None | List parking sessions |
| `GET` | `/api/alerts` | None | List recent security and safety alerts |
| `PATCH` | `/api/alerts/:id/ack` | None | Acknowledge/dismiss an alert |
| `POST` | `/api/events` | `x-api-key` | Ingest AI tracking/safety events (validated payload) |
| `GET` | `/api/v1/cameras/{camera_id}/zones` | `x-api-key` | Fetch that camera's persisted slot polygons |
| `POST` | `/api/v1/ai-events` | `x-api-key` | Ingest versioned canonical AI events |
| `WS` | `/ws/events` | None | Receive realtime events as `{ "event", "data" }` JSON |

## Dashboard service indicators and ML estimate
The dashboard's live badge reflects its native WebSocket connection. Its service strip checks the backend API and AI-service health, camera stream, OCR configuration, and whether the duration model is present. Recognized plates are shown from OCR events saved on parking sessions; AI snapshots are served from the AI service's `/media/alerts` endpoint.

The dashboard calls the FastAPI `/api/v1` endpoints, including `POST /api/v1/slots/allocate` and watchlist CRUD. Allocation reserves a slot; when a camera-frame `reference_point` is supplied, the backend selects the geometrically nearest slot by polygon centroid. Without a reference point, it deterministically sorts by zone and slot ID. Copy `frontend/.env.example` to `.env.local` to configure the optional `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_AI_STREAM_URL`, and `NEXT_PUBLIC_CAMERA_IDS` values.

The AI service exposes `GET /health` and `POST /ml/predict-duration`. The latter accepts `{"vehicleType":"car","arrivalHour":9,"weekday":0}` and returns an estimated stay in minutes. The estimate is a prototype trained on generated synthetic data; the current backend slot recommendation still uses its existing allocation rules and does not use this estimate to select a space.

## Event contract (ai-service → backend `POST /api/v1/ai-events`)
The AI dispatcher sends canonical snake_case fields and `event_type`; the backend also accepts
the older `type`, `trackId`, and `vehicleType` aliases for compatibility.

| event_type | fields | effect |
|---|---|---|
| `ENTRY` | track_id, vehicle_category, camera_id, plate_number? | creates a session; subsequent recognized-plate entry updates that session |
| `EXIT` | track_id, camera_id | closes the matching camera session and frees its slot |
| `ALERT` | alert_type, track_id, camera_id, message, snapshot_url? | raises a matching safety alert |
| `plate` (legacy) | track_id, plate | attaches plate and checks watchlist |
| `parked` (legacy) | track_id, slot_id | marks slot occupied |

Watchlist is **simulated** for the prototype (as stated in the proposal).
