# Backend Service

Node.js + Express + MongoDB backend with Socket.IO for real-time CCTV parking telemetry, event ingestion, and safety alerts.

## Setup & Running

```bash
cd backend
npm install
npm run seed      # Seeds 12 demo slots + 2 watchlist plates
npm run dev       # Starts server on http://localhost:5000 with nodemon
```

## REST API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | Health status and server time |
| `GET` | `/api/stats` | Public | Real-time overview metrics: `totalSlots`, `freeSlots`, `occupied`, `activeVehicles`, `todayEntries`, `openAlerts` |
| `GET` | `/api/slots` | Public | Full list of parking slots and status (`free`/`occupied`) |
| `GET` | `/api/slots/recommend?vehicleType=car` | Public | Recommends nearest available slot for vehicle type (`bike`, `car`, `suv`) |
| `GET` | `/api/sessions` | Public | List of parking sessions (active and past) |
| `GET` | `/api/alerts` | Public | Security and safety alerts |
| `PATCH` | `/api/alerts/:id/ack` | Public | Acknowledge/dismiss an alert |
| `POST` | `/api/events` | `x-api-key: dev-key` | AI event ingestion endpoint (validated) |

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
  -d '{"type":"wrong_parking","trackId":102,"plate":"RJ14XY9999","message":"Parked in restricted lane"}'
```

### 5. `crash`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"crash","message":"Collision detected in Zone A aisle","cameraId":"cam-1"}'
```

### 6. `exit`
```bash
curl -X POST http://localhost:5000/api/events \
  -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"type":"exit","trackId":101}'
```

### 7. Overview Statistics
```bash
curl http://localhost:5000/api/stats
```
