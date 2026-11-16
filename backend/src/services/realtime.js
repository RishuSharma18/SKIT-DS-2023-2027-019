import { randomUUID } from 'crypto';

const ALERT_TYPE = {
  stolen_vehicle: 'STOLEN_VEHICLE',
  crash: 'ACCIDENT',
  wrong_parking: 'WRONG_PARKING',
  overstay: 'OVERSTAY',
};

const EVENT_TYPE = {
  'slots:update': 'SLOT_UPDATE',
  'alert:new': 'ALERT',
  'session:new': 'ENTRY',
  'session:update': 'SESSION_UPDATE',
  'camera:occupancy': 'SLOT_UPDATE',
};

function plainValue(value) {
  if (Array.isArray(value)) return value.map(plainValue);
  return value && typeof value.toObject === 'function' ? value.toObject() : value;
}

function eventEnvelope(name, value) {
  const payload = plainValue(value);
  const record = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
  const eventType = name === 'session:update' && record.status === 'closed'
    ? 'EXIT'
    : EVENT_TYPE[name] || name.toUpperCase();
  const category = String(record.vehicle_category || record.vehicleCategory || record.vehicleType || '').toUpperCase();
  const vehicleCategory = ['TWO_WHEELER', 'COMPACT_CAR', 'SUV_SEDAN', 'HEAVY_VEHICLE'].includes(category)
    ? category
    : ['BIKE', 'MOTORBIKE', 'MOTORCYCLE'].includes(category)
      ? 'TWO_WHEELER'
      : ['TRUCK', 'BUS', 'HEAVY'].includes(category)
        ? 'HEAVY_VEHICLE'
        : category === 'SUV' || category === 'SEDAN'
          ? 'SUV_SEDAN'
          : record.vehicleType
            ? 'COMPACT_CAR'
            : null;
  return {
    event: name,
    event_id: record.event_id || record.eventId || randomUUID(),
    timestamp: record.updatedAt || record.createdAt || record.timestamp || new Date().toISOString(),
    camera_id: record.camera_id || record.cameraId || 'cam-1',
    track_id: record.track_id ?? record.trackId ?? null,
    vehicle_category: vehicleCategory,
    plate_number: record.plate_number || record.plateNumber || record.plate || null,
    slot_id: record.slot_id || record.slotId || null,
    event_type: eventType,
    alert_type: name === 'alert:new' ? ALERT_TYPE[record.type] || null : null,
    snapshot_url: record.snapshot_url || record.snapshotUrl || record.snapshot || null,
    payload,
  };
}

export function emitRealtime(io, name, value) {
  io.emit(name, value);
  if (typeof io.emitWebSocket === 'function') {
    io.emitWebSocket(eventEnvelope(name, value));
  }
}
