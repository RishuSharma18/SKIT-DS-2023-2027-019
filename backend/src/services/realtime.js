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
};

function plainValue(value) {
  return value && typeof value.toObject === 'function' ? value.toObject() : value;
}

function eventEnvelope(name, value) {
  const payload = plainValue(value);
  const record = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
  const eventType = name === 'session:update' && record.status === 'closed'
    ? 'EXIT'
    : EVENT_TYPE[name] || name.toUpperCase();
  return {
    event_id: String(record._id || record.id || `${name}-${Date.now()}`),
    timestamp: record.updatedAt || record.createdAt || record.timestamp || new Date().toISOString(),
    camera_id: record.cameraId || 'CAM_01',
    track_id: record.trackId ?? null,
    vehicle_category: record.vehicleType || null,
    plate_number: record.plate || null,
    slot_id: record.slotId || null,
    event_type: eventType,
    alert_type: name === 'alert:new' ? ALERT_TYPE[record.type] || null : null,
    snapshot_url: record.snapshot || null,
    payload,
  };
}

export function emitRealtime(io, name, value) {
  io.emit(name, value);
  const clients = io.nativeWebSocketClients || [];
  const message = JSON.stringify(eventEnvelope(name, value));
  for (const client of clients) {
    if (client.readyState === 1) client.send(message);
  }
}
