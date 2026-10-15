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
npm run dev           # http://localhost:5173

# 4. ai-service (terminal 3)
cd ai-service
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Copy .env.example to .env if .env does not already exist; merge settings instead of overwriting an existing .env.
# Record or download a parking video to samples/parking.mp4 (video files are gitignored).
# Use tools/draw_slots.py to draw slot polygons for that video before running the pipeline.
python tools/draw_slots.py --source samples/parking.mp4 --out config/slots.json
python tools/detect_demo.py --source samples/parking.mp4
# Review boxes and IDs; optionally retry with --conf 0.3 to compare detection sensitivity.
# If the printed largest-gap suggestion matches cars vs SUVs in your footage, tune SUV_AREA_RATIO in .env.
python run_pipeline.py --show                          # dev window, press q to quit
uvicorn app.main:app --port 8000                       # or: serve /stream for the dashboard
```

On Windows PowerShell, the equivalent AI-service setup is:

```powershell
cd ai-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
New-Item -ItemType Directory -Force samples | Out-Null
# Put your parking video at samples\parking.mp4, then:
python tools\draw_slots.py --source samples\parking.mp4 --out config\slots.json
python tools\detect_demo.py --source samples\parking.mp4
python run_pipeline.py --show
```

The slot polygons must be drawn on the actual video frame; the committed slot coordinates are examples,
not calibrated coordinates for your camera. Work with the dashboard owner to agree on the parking-slot
layout and vehicle types before saving `config/slots.json`. In COCO, YOLO labels motorcycles as `bike`,
cars as `car`, and buses/trucks as `suv`; SUV detection is an approximation based on those classes and
the configurable bounding-box area ratio, not a dedicated SUV class. Disable OCR in `.env` with
`ENABLE_OCR=0` for detection-only runs when EasyOCR is not needed.

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
| `GET` | `/api/slots` | None | List all parking slots and real-time statuses |
| `GET` | `/api/slots/recommend?vehicleType=car` | None | Recommend best available slot for `bike`, `car`, or `suv` |
| `GET` | `/api/sessions` | None | List parking sessions |
| `GET` | `/api/alerts` | None | List recent security and safety alerts |
| `PATCH` | `/api/alerts/:id/ack` | None | Acknowledge/dismiss an alert |
| `POST` | `/api/events` | `x-api-key` | Ingest AI tracking/safety events (validated payload) |

## Event contract (ai-service → backend `POST /api/events`)
| type | fields | effect |
|---|---|---|
| `entry` | trackId, vehicleType, plate? | creates session, returns recommended slot |
| `plate` | trackId, plate | attaches plate, checks watchlist |
| `parked` | trackId, slotId | marks slot occupied |
| `exit` | trackId | closes session, stores duration, frees slot |
| `wrong_parking` | trackId, plate?, message? | raises alert |
| `crash` | message?, snapshot? | raises alert |

Watchlist is **simulated** for the prototype (as stated in the proposal).
