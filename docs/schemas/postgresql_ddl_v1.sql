-- PostgreSQL Schema DDL Specifications v1.0
-- Smart CCTV Parking & Safety System
-- Author: Vaibhav Soni (Backend Lead)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Parking Slots Table
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id VARCHAR(32) PRIMARY KEY,
    zone VARCHAR(64) NOT NULL,
    allowed_category VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE',
    polygon_coords JSONB NOT NULL,
    current_track_id INTEGER NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_parking_slots_zone ON parking_slots(zone);
CREATE INDEX IF NOT EXISTS idx_parking_slots_status ON parking_slots(status);
CREATE INDEX IF NOT EXISTS idx_parking_slots_category ON parking_slots(allowed_category);

-- 2. Vehicle Sessions Table
CREATE TABLE IF NOT EXISTS vehicle_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id INTEGER NOT NULL,
    plate_number VARCHAR(32) NULL,
    vehicle_category VARCHAR(32) NOT NULL,
    assigned_slot_id VARCHAR(32) REFERENCES parking_slots(slot_id) ON DELETE SET NULL,
    actual_slot_id VARCHAR(32) REFERENCES parking_slots(slot_id) ON DELETE SET NULL,
    camera_id VARCHAR(64) NULL,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exit_time TIMESTAMP WITH TIME ZONE NULL,
    duration_minutes DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    overstay_alerted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_track ON vehicle_sessions(track_id);
CREATE INDEX IF NOT EXISTS idx_sessions_plate ON vehicle_sessions(plate_number);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON vehicle_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_entry ON vehicle_sessions(entry_time);

-- 3. Security Watchlist Table
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(32) UNIQUE NOT NULL,
    reason TEXT NOT NULL,
    added_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist(is_active);
CREATE INDEX IF NOT EXISTS idx_watchlist_plate ON watchlist(plate_number);

-- 4. Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'MEDIUM',
    plate_number VARCHAR(32) NULL,
    slot_id VARCHAR(32) NULL,
    camera_id VARCHAR(64) NULL,
    snapshot_url TEXT NULL,
    message TEXT NOT NULL,
    is_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(is_acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
