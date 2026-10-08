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
cp .env.example .env
# put a parking video in ai-service/samples/parking.mp4, then edit config/slots.json to match it
python run_pipeline.py --show                          # dev window, press q to quit
uvicorn app.main:app --port 8000                       # or: serve /stream for the dashboard
```

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
