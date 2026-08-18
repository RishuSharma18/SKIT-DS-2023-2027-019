# Database Entity Relationship Specification

Comprehensive entity-relationship model and schema specifications for the AI-Powered Smart CCTV Parking & Safety System.

## Architecture Overview
The relational data store manages high-throughput edge telemetry, vehicle lifecycle sessions, security watchlists, and safety incident alerts.

```mermaid
erDiagram
    PARKING_SLOTS ||--o{ VEHICLE_SESSIONS : "hosts"
    PARKING_SLOTS ||--o{ ALERTS : "records"
    WATCHLIST ||--o{ ALERTS : "triggers"
    CAMERA_ZONES ||--o{ PARKING_SLOTS : "maps"

    PARKING_SLOTS {
        string slot_id PK
        string zone
        string allowed_category
        string status
        jsonb polygon_coords
        int current_track_id
        timestamp created_at
        timestamp updated_at
    }

    VEHICLE_SESSIONS {
        uuid session_id PK
        int track_id
        string plate_number
        string vehicle_category
        string assigned_slot_id FK
        string actual_slot_id FK
        timestamp entry_time
        timestamp exit_time
        float duration_minutes
        string status
        boolean overstay_alerted
    }

    WATCHLIST {
        int id PK
        string plate_number UK
        string reason
        string added_by
        timestamp created_at
        boolean is_active
    }

    ALERTS {
        uuid alert_id PK
        string alert_type
        string severity
        string plate_number
        string slot_id FK
        string camera_id
        string snapshot_url
        string message
        boolean is_acknowledged
        timestamp created_at
    }

    CAMERA_ZONES {
        string camera_id PK
        string zone_name
        jsonb slot_polygons
        jsonb no_parking_zones
        jsonb tripwires
        timestamp updated_at
    }
```

## Entity Specifications & Constraints

### 1. `parking_slots`
- **Primary Key**: `slot_id` (e.g., `A-01`, `B-04`).
- **Allowed Categories**:
  - `TWO_WHEELER`: Standard motorcycle / scooter slots.
  - `COMPACT_CAR`: Standard sedans and hatchbacks.
  - `SUV_SEDAN`: Mid-to-full size SUVs and larger sedans.
  - `HEAVY_VEHICLE`: Delivery trucks, buses, maintenance transports.
- **Occupancy Status**: `AVAILABLE`, `RESERVED`, `OCCUPIED`, `VIOLATION`.

### 2. `vehicle_sessions`
- **Lifecycle Tracking**:
  - Tracks vehicle from entrance tripwire crossing (`entry_time`) to parking slot allocation and final lot departure (`exit_time`).
  - `duration_minutes` is automatically computed at checkout.

### 3. `watchlist`
- **Index**: Unique B-tree index on `plate_number`.
- Plates stored normalized in uppercase without spaces or punctuation.

### 4. `alerts`
- High-priority security and safety logs: `STOLEN_VEHICLE`, `ACCIDENT`, `WRONG_PARKING`, `OVERSTAY`.
