# AI-Powered Smart CCTV Parking & Vehicle Safety System

Final-year B.Tech project, CSE (Data Science), SKIT Jaipur, batch 2023-27. Guide: Dr. Nilam Chaudhary.

CCTV video → **AI service** (YOLOv8 + EasyOCR) → **Backend** (Express + MongoDB) → **Dashboard** (React).

```
 ┌──────────┐  frames  ┌─────────────────┐  REST events  ┌────────────────┐  Socket.IO  ┌───────────────┐
 │ CCTV /   │ ───────► │  ai-service     │ ────────────► │  backend       │ ──────────► │  frontend     │
 │ video    │          │  Python+FastAPI │  x-api-key    │  Node+Express  │  + REST     │  React (Vite) │
 └──────────┘          │  YOLOv8,OpenCV, │               │  MongoDB       │             │  dashboard    │
                       │  EasyOCR        │               └────────────────┘             └───────────────┘
                       └─────────────────┘
```

## Folder structure
| Folder | Owner | What lives here |
|---|---|---|
| `ai-service/` | Rishu (detection), Nandani (OCR) | Detection, tracking, plate OCR, slot/violation logic |
| `backend/` | Vaibhav | REST API, MongoDB models, event handling, alerts, Socket.IO |
| `frontend/` | Bhumi | React dashboard |
| `docs/` | everyone | Plan, Git workflow, report material |

## Quick start (first time)
Prereqs: Node 18+, Python 3.10+, Docker (for MongoDB) or a local MongoDB.

```bash
# 1. database
docker compose up -d

# 2. backend  (terminal 1)
cd backend
cp .env.example .env
npm install
npm run seed          # creates 12 slots + 2 demo watchlist plates
npm run dev           # http://localhost:5000/api/health

# 3. frontend (terminal 2)
cd frontend
npm install
npm run dev           # http://localhost:5173; proxies AI requests to port 8001

# 4. ai-service (terminal 3)
cd ai-service
python -m venv .venv
source .venv/bin/activate                             # Windows Git Bash: source .venv/Scripts/activate
python -m pip install -r requirements.txt
# Train the optional duration-estimation prototype used by the dashboard.
python ml/generate_data.py
python ml/train_duration_model.py
# Copy .env.example to .env if .env does not already exist; merge settings instead of overwriting an existing .env.
# Record or download a parking video to samples/parking.mp4 (video files are gitignored).
# Use tools/draw_slots.py to draw slot polygons for that video before running the pipeline.
python tools/draw_slots.py --source samples/parking.mp4 --out config/slots.json
python tools/detect_demo.py --source samples/parking.mp4 --imgsz 1280 --conf 0.25
# Larger imgsz can find more distant/small vehicles but is slower; compare with --imgsz 640.
# Review boxes and IDs; tune CONFIDENCE and YOLO_IMAGE_SIZE in .env for your camera.
# Run the AI API in this terminal for the dashboard camera stream and health checks:
uvicorn app.main:app --host 127.0.0.1 --port 8001
# For a standalone local preview instead, stop Uvicorn and run:
python run_pipeline.py --show
```

On Windows PowerShell, the equivalent AI-service setup is:

```powershell
cd ai-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Train the optional dashboard duration estimate (uses synthetic prototype data).
python ml\generate_data.py
python ml\train_duration_model.py
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
New-Item -ItemType Directory -Force samples | Out-Null
# Put your parking video at samples\parking.mp4, then:
python tools\draw_slots.py --source samples\parking.mp4 --out config\slots.json
python tools\detect_demo.py --source samples\parking.mp4
# For dashboard integration, run the AI API on port 8001:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The current `ai-service/config/slots.json` maps five marked car spaces from the included sample video's
3840x2160 frame; it is only suitable for that same fixed camera and frame geometry, not a confirmed
physical facility. The dashboard identifies prerecorded input as video replay and hides live counts
and recommendations until a webcam or network camera and matching spaces are configured. It only
displays the spaces mapped by the active camera; occupancy is refreshed from detections in those bays.
For a live camera, missing mapped slots are registered and their status is synchronized; unrelated
slots are left alone. Sample-video occupancy is broadcast as a temporary estimate and is not saved,
and replay-generated sessions and alerts are disabled.
YOLO's COCO classes include motorcycle and car (SUVs are included in car); COCO cannot reliably
distinguish an SUV from another car. A separately trained classifier is needed for that distinction.
Entries are created only after a tracked vehicle remains inside a configured bay. Disable OCR in
`.env` with `ENABLE_OCR=0` for detection-only runs when EasyOCR is not needed. Inference defaults
to 1280px and uses overlapping tiles for high-resolution sources to improve small-vehicle recall, at
a higher processing cost. Smaller sources use a single full-frame tile. CPU inference may not keep up
with a live stream; a supported GPU or lower `YOLO_IMAGE_SIZE` may be needed. The camera overlay
legend explains box/bay colors; blue boxes are detected vehicles, red boxes are confirmed in a mapped
bay, green bays are available, and red bays are occupied. Detection counts are not ground-truth
accuracy measurements; validate on annotated frames from the target camera.

### Test a crash alert end to end

The synthetic tests cover the detector and backend crash-event contract:

```bash
cd ai-service && python tests_crash.py
cd ai-service && python tests_vehicle.py && python tests_detection.py
cd ../backend && npm test
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
| `GET` | `/api/health` | None | Health check & server status |
| `GET` | `/api/stats` | None | Overview metrics (total slots, free, occupied, active vehicles, today's entries, open alerts) |
| `GET` | `/api/analytics/hourly` | None | Today's parking entries grouped by hour |
| `GET` | `/api/slots` | None | List all parking slots and real-time statuses |
| `GET` | `/api/slots/recommend?vehicleType=car` | None | Recommend best available slot for `bike`, `car`, or `suv` |
| `GET` | `/api/sessions` | None | List parking sessions |
| `GET` | `/api/alerts` | None | List recent security and safety alerts |
| `PATCH` | `/api/alerts/:id/ack` | None | Acknowledge/dismiss an alert |
| `POST` | `/api/events` | `x-api-key` | Ingest AI tracking/safety events (validated payload) |

## Dashboard service indicators and ML estimate
The dashboard's live badge reflects the backend Socket.IO connection. Its service strip checks the backend API and AI-service health, camera stream, OCR configuration, and whether the duration model is present. Recognized plates are shown from OCR events saved on parking sessions; safety-alert snapshots link to the backend `/uploads` endpoint.

The dashboard also supports the `/api/v1` aliases for the REST endpoints, `POST /api/v1/slots/allocate`, and `GET/POST/PUT/DELETE /api/v1/watchlist`. It receives standardized live event envelopes from the backend at `/ws/events`; existing Socket.IO clients remain supported. Copy `frontend/.env.example` to `.env.local` to configure the optional `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_AI_STREAM_URL`, and `NEXT_PUBLIC_CAMERA_IDS` values.

The AI service exposes `GET /health` and `POST /ml/predict-duration`. The latter accepts `{"vehicleType":"car","arrivalHour":9,"weekday":0}` and returns an estimated stay in minutes. The estimate is a prototype trained on generated synthetic data; the current backend slot recommendation still uses its existing allocation rules and does not use this estimate to select a space.

## Event contract (ai-service → backend `POST /api/events`)
| type | fields | effect |
|---|---|---|
| `entry` | trackId, vehicleType, plate? | creates session, returns recommended slot |
| `plate` | trackId, plate | attaches plate, checks watchlist |
| `parked` | trackId, slotId | marks slot occupied |
| `exit` | trackId | closes session, stores duration, frees slot |
| `wrong_parking` | trackId, plate?, message? | raises alert |
| `crash` | trackIds? (two IDs), message?, snapshot? | raises high-severity alert; dashboard shows both track IDs |

Watchlist is **simulated** for the prototype (as stated in the proposal).
