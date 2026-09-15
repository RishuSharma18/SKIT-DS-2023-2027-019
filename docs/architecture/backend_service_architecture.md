# Backend Service Architecture & Pipeline Data Flow

Architectural specification of the AI-driven CCTV parking backend service orchestration.

```mermaid
flowchart TD
    subgraph Edge Layer
        Cam1["Edge Camera 1 (Entrance)"]
        Cam2["Edge Camera 2 (Zone A / B)"]
        Cam3["Edge Camera 3 (Exit)"]
    end

    subgraph AI Processing
        YOLO["YOLOv8 Vehicle Detector"]
        Tracker["ByteTrack Multi-Object Tracker"]
        OCR["EasyOCR License Plate Recognition"]
    end

    subgraph Backend Orchestration Layer
        Ingest["Event Ingestion Gateway (/api/v1/ai-events)"]
        AllocEngine["Smart Slot Allocation Engine"]
        OverstayWorker["60s Overstay Background Worker"]
        IdempotencyCache["Redis Idempotency & Watchlist Cache"]
    end

    subgraph Persistent Storage
        PG[(PostgreSQL Database)]
        DiskStore[("/uploads Media Storage")]
    end

    subgraph Clients
        WSHub["WebSocket Event Hub (/ws/events)"]
        OperatorUI["Security Operations Dashboard"]
    end

    Cam1 & Cam2 & Cam3 --> YOLO --> Tracker --> OCR
    OCR -->|Telemetry POST| Ingest
    Ingest --> IdempotencyCache
    Ingest --> AllocEngine
    AllocEngine --> PG
    Ingest --> PG
    Ingest -->|Base64 Snapshots| DiskStore
    OverstayWorker -->|Periodic Scan| PG
    Ingest & OverstayWorker -->|Live Broadcast| WSHub --> OperatorUI
```

## Core Service Layers

1. **Edge Ingestion Pipeline**:
   - Ingests canonical frame events: `entry`, `plate`, `parked`, `exit`, `crash`, `wrong_parking`.
   - Thread-safe deduplication with Redis TTL guarantees zero duplicate session records.

2. **Smart Allocation Engine**:
   - Queries available slots within the targeted zone.
   - Applies strict category fallback rules to optimize lot utilization.

3. **Background Overstay Daemon**:
   - Runs asynchronously every 60 seconds.
   - Flags active vehicles exceeding configurable duration thresholds.
