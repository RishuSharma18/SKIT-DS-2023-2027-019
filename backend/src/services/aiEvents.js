import AiEventReceipt from '../models/AiEventReceipt.js';
import { handleEvent } from './events.js';
import { emitRealtime } from './realtime.js';

const VEHICLE_TYPE_MAP = {
  TWO_WHEELER: 'bike',
  COMPACT_CAR: 'car',
  SUV_SEDAN: 'suv',
  HEAVY_VEHICLE: 'heavy_vehicle',
};
const ALERT_TYPE_MAP = {
  STOLEN_VEHICLE: 'stolen_vehicle',
  ACCIDENT: 'crash',
  WRONG_PARKING: 'wrong_parking',
  OVERSTAY: 'overstay',
};

function toLegacyEvent(event) {
  const common = {
    trackId: event.track_id,
    cameraId: event.camera_id,
    plate: event.plate_number ?? null,
    vehicleType: VEHICLE_TYPE_MAP[event.vehicle_category] || 'car',
    slotId: event.slot_id ?? null,
    snapshot: event.snapshot_url ?? null,
    timestamp: event.timestamp,
    message: event.message,
  };
  if (event.event_type === 'ENTRY') return { ...common, type: 'entry' };
  if (event.event_type === 'EXIT') return { ...common, type: 'exit' };
  return {
    ...common,
    type: ALERT_TYPE_MAP[event.alert_type],
    ...(event.alert_type === 'ACCIDENT' && event.track_id !== undefined
      ? { trackIds: [event.track_id, ...(event.related_track_ids || [])].slice(0, 2) }
      : {}),
  };
}

export async function handleAiEvent(io, event) {
  if (await AiEventReceipt.exists({ event_id: event.event_id })) {
    return { accepted: true, duplicate: true, event_id: event.event_id };
  }

  const result = await handleEvent(io, toLegacyEvent(event));
  try {
    await AiEventReceipt.create({
      event_id: event.event_id,
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    });
  } catch (error) {
    if (error.code !== 11000) throw error;
    return { accepted: true, duplicate: true, event_id: event.event_id };
  }
  emitRealtime(io, 'ai:event', event);
  return { accepted: true, duplicate: false, event_id: event.event_id, result };
}
