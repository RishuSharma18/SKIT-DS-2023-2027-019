# Production Deployment & Operations Runbook

Comprehensive deployment runbook for orchestrating the AI CCTV Parking Backend.

## System Prerequisites
- Docker Engine >= 24.0.0 & Docker Compose v2
- PostgreSQL 15+ with `uuid-ossp`
- Redis 7+ with persistent append-only file (AOF)
- Python 3.11+ / Node.js 18+

## Quickstart Deployment Steps

```bash
# 1. Clone repository
git clone https://github.com/RishuSharma18/SKIT-DS-2023-2027-019.git
cd SKIT-DS-2023-2027-019

# 2. Launch persistent services via Docker
docker-compose up -d postgres redis

# 3. Apply database migrations
cd backend
alembic upgrade head

# 4. Populate slot geometry and security watchlist
python scripts/seed.py

# 5. Start production FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4
```

## Health Verification Checks
- **Health check**: `curl -f http://localhost:5000/api/health`
- **Interactive OpenAPI Documentation**: `http://localhost:5000/docs`
- **Telemetry Ingestion Health**: `POST /api/v1/ai-events` with test ping
