import { Router } from 'express';
import ParkingSlot from '../models/ParkingSlot.js';
import ParkingSession from '../models/ParkingSession.js';
import Watchlist from '../models/Watchlist.js';
import Alert from '../models/Alert.js';
import CameraZone from '../models/CameraZone.js';
import apiKey from '../middleware/apiKey.js';
import validateEvent from '../middleware/validateEvent.js';
import validateAiEvent from '../middleware/validateAiEvent.js';
import { handleEvent } from '../services/events.js';
import { handleAiEvent } from '../services/aiEvents.js';
import { recommendSlot } from '../services/allocation.js';

const r = Router();
const wrap = (fn) => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);
const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const TYPE_TO_CATEGORY = {
  bike: 'TWO_WHEELER',
  car: 'COMPACT_CAR',
  suv: 'SUV_SEDAN',
  heavy_vehicle: 'HEAVY_VEHICLE',
};
const CATEGORY_TO_TYPE = Object.fromEntries(
  Object.entries(TYPE_TO_CATEGORY).map(([type, category]) => [category, type]),
);
const STATUS_TO_CATEGORY = {
  free: 'AVAILABLE',
  occupied: 'OCCUPIED',
  reserved: 'RESERVED',
  violation: 'VIOLATION',
};
const isPolygon = (polygon) => Array.isArray(polygon) && polygon.length >= 3
  && polygon.every((point) => Array.isArray(point) && point.length === 2
    && point.every((coordinate) => Number.isFinite(coordinate)));
const hasUniqueIds = (items, key) => {
  const ids = items.map((item) => item && typeof item === 'object' ? item[key] : undefined);
  return ids.every((id) => typeof id === 'string' && id.trim() === id && id.length > 0)
    && new Set(ids).size === ids.length;
};
const validateZoneConfig = (body) => {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return false;
  if (body.no_parking_zones !== undefined
      && (!Array.isArray(body.no_parking_zones)
        || !hasUniqueIds(body.no_parking_zones, 'zone_id')
        || !body.no_parking_zones.every((zone) => isPolygon(zone.polygon)))) return false;
  if (body.tripwires !== undefined
      && (!Array.isArray(body.tripwires)
        || !hasUniqueIds(body.tripwires, 'tripwire_id')
        || !body.tripwires.every((wire) => ['ENTRY', 'EXIT'].includes(wire.event_type)
          && Array.isArray(wire.line) && wire.line.length === 2
          && wire.line.every((point) => Array.isArray(point) && point.length === 2
            && point.every((coordinate) => Number.isFinite(coordinate)))))) return false;
  if (body.slots !== undefined
      && (!Array.isArray(body.slots)
        || !hasUniqueIds(body.slots, 'slot_id')
        || !body.slots.every((slot) => typeof slot.slot_id === 'string'
          && CATEGORY_TO_TYPE[slot.vehicle_category]
          && isPolygon(slot.polygon)))) return false;
  return ['slots', 'no_parking_zones', 'tripwires'].some((key) => body[key] !== undefined);
};

r.get('/health', (req, res) => res.json({ ok: true, time: new Date() }));

// ---- Shared camera zone configuration and AI event contract
r.get('/v1/cameras/:cameraId/zones', apiKey, wrap(async (req, res) => {
  const [slots, zones] = await Promise.all([
    ParkingSlot.find({ cameraId: req.params.cameraId }).lean(),
    CameraZone.findOne({ camera_id: req.params.cameraId }).lean(),
  ]);
  res.json({
    camera_id: req.params.cameraId,
    slots: slots.filter((slot) => slot.polygon?.length >= 3).map((slot) => ({
      slot_id: slot.slotId,
      vehicle_category: TYPE_TO_CATEGORY[slot.type],
      status: STATUS_TO_CATEGORY[slot.status] || 'AVAILABLE',
      polygon: slot.polygon,
    })),
    no_parking_zones: zones?.no_parking_zones || [],
    tripwires: zones?.tripwires || [],
  });
}));

r.put('/v1/cameras/:cameraId/zones', apiKey, wrap(async (req, res) => {
  if (!validateZoneConfig(req.body)) {
    return res.status(400).json({
      error: 'Zones require polygon arrays with at least three [x,y] points; tripwires require two [x,y] endpoints and ENTRY or EXIT.',
    });
  }
  if (req.body.slots) {
    const operations = req.body.slots.map((slot) => ({
      updateOne: {
        filter: { slotId: slot.slot_id },
        update: {
          $set: {
            cameraId: req.params.cameraId,
            type: CATEGORY_TO_TYPE[slot.vehicle_category],
            polygon: slot.polygon,
          },
          $setOnInsert: {
            slotId: slot.slot_id,
            zone: slot.slot_id.includes('-') ? slot.slot_id.slice(0, slot.slot_id.lastIndexOf('-')) : 'A',
          },
        },
        upsert: true,
      },
    }));
    if (operations.length) await ParkingSlot.bulkWrite(operations);
  }

  const zoneUpdate = {};
  for (const key of ['no_parking_zones', 'tripwires']) {
    if (req.body[key] !== undefined) zoneUpdate[key] = req.body[key];
  }
  const zones = Object.keys(zoneUpdate).length
    ? await CameraZone.findOneAndUpdate(
      { camera_id: req.params.cameraId },
      { $set: zoneUpdate, $setOnInsert: { camera_id: req.params.cameraId } },
      { new: true, upsert: true, runValidators: true },
    )
    : null;
  res.json({ ok: true, zones });
}));

r.post('/v1/ai-events', apiKey, validateAiEvent, wrap(async (req, res) => {
  const result = await handleAiEvent(req.app.get('io'), req.body);
  res.status(result.duplicate ? 200 : 201).json(result);
}));

// ---- Stats (parking overview)
r.get('/stats', wrap(async (req, res) => {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);

  const [totalSlots, freeSlots, occupied, activeVehicles, todayEntries, openAlerts] = await Promise.all([
    ParkingSlot.countDocuments(),
    ParkingSlot.countDocuments({ status: 'free' }),
    ParkingSlot.countDocuments({ status: 'occupied' }),
    ParkingSession.countDocuments({ status: 'active' }),
    ParkingSession.countDocuments({ entryTime: { $gte: startOfToday } }),
    Alert.countDocuments({ acknowledged: false }),
  ]);

  res.json({
    totalSlots,
    freeSlots,
    occupied,
    occupiedSlots: occupied,
    activeVehicles,
    todayEntries,
    openAlerts,
  });
}));

// ---- Analytics: hourly entries for today (or ?date=YYYY-MM-DD)
r.get('/analytics/hourly', wrap(async (req, res) => {
  const dateBase = req.query.date ? new Date(req.query.date) : new Date();
  const startOfDay = new Date(dateBase);
  startOfDay.setHours(0, 0, 0, 0);

  const endOfDay = new Date(dateBase);
  endOfDay.setHours(23, 59, 59, 999);

  const sessions = await ParkingSession.find(
    { entryTime: { $gte: startOfDay, $lte: endOfDay } },
    { entryTime: 1 }
  );

  const hourly = Array.from({ length: 24 }, (_, i) => ({ hour: i, entries: 0 }));
  for (const s of sessions) {
    if (s.entryTime) {
      const h = new Date(s.entryTime).getHours();
      if (h >= 0 && h < 24) {
        hourly[h].entries++;
      }
    }
  }

  if (req.query.nonzero === 'true') {
    return res.json(hourly.filter((h) => h.entries > 0));
  }

  res.json(hourly);
}));

// ---- Slots
r.get('/slots', wrap(async (req, res) => res.json(await ParkingSlot.find().sort({ slotId: 1 }))));
r.get('/slots/recommend', wrap(async (req, res) => {
  const slotIds = typeof req.query.slotIds === 'string'
    ? req.query.slotIds.split(',').map((slotId) => slotId.trim()).filter(Boolean).slice(0, 100)
    : [];
  const slot = await recommendSlot(req.query.type || req.query.vehicleType || 'car', slotIds);
  res.json({ slot });
}));

// ---- Sessions (check-in / check-out history)
r.get('/sessions', wrap(async (req, res) => {
  const filter = {};

  if (req.query.plate) {
    filter.plate = { $regex: escapeRegex(req.query.plate.trim()), $options: 'i' };
  }
  if (req.query.status) {
    filter.status = req.query.status.trim();
  }
  if (req.query.vehicleType) {
    filter.vehicleType = req.query.vehicleType.trim();
  }
  if (req.query.slotId) {
    filter.slotId = req.query.slotId.trim();
  }
  if (req.query.cameraId) {
    filter.cameraId = req.query.cameraId.trim();
  }

  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const limit = req.query.limit !== undefined
    ? Math.max(1, parseInt(req.query.limit, 10) || 20)
    : (req.query.page ? 20 : 200);
  const skip = (page - 1) * limit;

  const [total, sessions] = await Promise.all([
    ParkingSession.countDocuments(filter),
    ParkingSession.find(filter).sort({ createdAt: -1 }).skip(skip).limit(limit),
  ]);

  res.setHeader('X-Total-Count', total.toString());
  res.setHeader('Access-Control-Expose-Headers', 'X-Total-Count');
  res.json(sessions);
}));

// ---- Watchlist (simulated stolen-vehicle DB)
r.get('/watchlist', wrap(async (req, res) => res.json(await Watchlist.find().sort({ createdAt: -1 }))));
r.post('/watchlist', wrap(async (req, res) => res.status(201).json(await Watchlist.create(req.body))));
r.delete('/watchlist/:id', wrap(async (req, res) => {
  await Watchlist.findByIdAndDelete(req.params.id);
  res.status(204).end();
}));

// ---- Alerts
r.get('/alerts', wrap(async (req, res) => {
  const filter = {};

  if (req.query.type && req.query.type !== 'all') {
    filter.type = req.query.type.trim();
  }
  if (req.query.acknowledged !== undefined && req.query.acknowledged !== '') {
    const val = String(req.query.acknowledged).toLowerCase().trim();
    if (val === 'true') {
      filter.acknowledged = true;
    } else if (val === 'false') {
      filter.acknowledged = false;
    }
  }
  if (req.query.severity) {
    filter.severity = req.query.severity.trim();
  }
  if (req.query.plate) {
    filter.plate = { $regex: escapeRegex(req.query.plate.trim()), $options: 'i' };
  }
  if (req.query.slotId) {
    filter.slotId = req.query.slotId.trim();
  }
  if (req.query.cameraId) {
    filter.cameraId = req.query.cameraId.trim();
  }

  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const limit = req.query.limit !== undefined
    ? Math.max(1, parseInt(req.query.limit, 10) || 20)
    : (req.query.page ? 20 : 100);
  const skip = (page - 1) * limit;

  const [total, alerts] = await Promise.all([
    Alert.countDocuments(filter),
    Alert.find(filter).sort({ createdAt: -1 }).skip(skip).limit(limit),
  ]);

  res.setHeader('X-Total-Count', total.toString());
  res.setHeader('Access-Control-Expose-Headers', 'X-Total-Count');
  res.json(alerts);
}));

r.patch('/alerts/:id/ack', wrap(async (req, res) =>
  res.json(await Alert.findByIdAndUpdate(req.params.id, { acknowledged: true }, { new: true }))));

// ---- Ingestion from the AI service
r.post('/events', apiKey, validateEvent, wrap(async (req, res) => {
  res.status(201).json(await handleEvent(req.app.get('io'), req.body));
}));

export default r;
