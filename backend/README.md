# Backend Service

Node.js + Express + MongoDB backend with Socket.IO for real-time CCTV parking telemetry, event ingestion, and safety alerts.

## Setup & Running

```bash
cd backend
npm install
npm run seed      # Seeds demo slots + watchlist plates
npm run dev       # Starts server on http://localhost:5000 with nodemon
npm run simulate  # Simulates live camera events (or node src/scripts/simulate.js)
```

## REST API Overview

See [API.md](../docs/API.md) for full endpoint specifications, request bodies, and response examples.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | Health status and server time |
| `GET` | `/api/stats` | Public | Real-time overview metrics: `totalSlots`, `freeSlots`, `occupied`, `activeVehicles`, `todayEntries`, `openAlerts` |
| `GET` | `/api/analytics/hourly` | Public | Hourly entry count for today `[{hour: 0, entries: 0}, ...]` |
| `GET` | `/api/slots` | Public | Full list of parking slots and status (`free`/`occupied`) |
| `GET` | `/api/slots/recommend?type=car` | Public | Recommends nearest available slot for vehicle type (`bike`, `car`, `suv`) |
| `GET` | `/api/sessions` | Public | Filterable & paginated parking sessions (`?plate=RJ14&status=closed&page=1&limit=20`) |
| `GET` | `/api/alerts` | Public | Filterable & paginated alerts (`?type=crash&acknowledged=false&page=1&limit=20`) |
| `PATCH` | `/api/alerts/:id/ack` | Public | Acknowledge/dismiss an alert |
| `GET` | `/api/watchlist` | Public | List of flagged license plates |
| `POST` | `/api/watchlist` | Public | Add license plate to watchlist |
| `DELETE` | `/api/watchlist/:id` | Public | Remove license plate from watchlist |
| `POST` | `/api/events` | `x-api-key: dev-key` | AI event ingestion endpoint (supports base64 snapshots) |
| `GET` | `/uploads/:filename` | Public | Statically serves saved snapshot images |

## Pagination & Headers

For `GET /api/sessions` and `GET /api/alerts`:
- Responses return a standard JSON Array (`[...]`).
- Total matching records are returned in the `X-Total-Count` response header.
- CORS exposed headers include `X-Total-Count`.

## Overstay Detection

The background worker runs `checkOverstays` every 1 minute in `server.js`. Vehicles remaining in active status longer than `OVERSTAY_HOURS` (default: 4 hours) generate an `overstay` alert and broadcast via Socket.IO.

## Testing Events via curl

Replace `localhost:5000` and API key as needed:

### 1. `entry`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"entry","trackId":101,"vehicleType":"car","plate":"RJ14AB1234"}'
```

### 2. `plate`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"plate","trackId":101,"plate":"RJ14AB1234"}'
```

### 3. `parked`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"parked","trackId":101,"slotId":"A-04"}'
```

### 4. `wrong_parking`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"wrong_parking","trackId":102,"plate":"HR26DK2001","message":"Parked in restricted lane"}'
```

### 5. `crash` (with base64 snapshot)
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"crash","message":"Collision detected in Zone A aisle","cameraId":"cam-1","snapshot":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="}'
```

### 6. `stolen_vehicle` (with base64 snapshot)
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"stolen_vehicle","plate":"RJ14AB1234","message":"Stolen vehicle detected","cameraId":"cam-1","snapshot":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="}'
```

### 7. `exit`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"exit","trackId":101}'
```

### 8. Filter Queries
```bash
# Filter closed sessions with plate RJ14
curl -i "http://localhost:5000/api/sessions?plate=RJ14&status=closed&page=1&limit=20"

# Filter unacknowledged crash alerts
curl -i "http://localhost:5000/api/alerts?type=crash&acknowledged=false&page=1&limit=20"
```
