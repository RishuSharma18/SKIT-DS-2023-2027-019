import { Router } from 'express';
import ParkingSlot from '../models/ParkingSlot.js';
import ParkingSession from '../models/ParkingSession.js';
import Watchlist from '../models/Watchlist.js';
import Alert from '../models/Alert.js';
import apiKey from '../middleware/apiKey.js';
import validateEvent from '../middleware/validateEvent.js';
import { handleEvent } from '../services/events.js';
import { recommendSlot } from '../services/allocation.js';

const r = Router();
const wrap = (fn) => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);
const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

r.get('/health', (req, res) => res.json({ ok: true, time: new Date() }));

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
r.post('/slots/allocate', wrap(async (req, res) => {
  const category = String(req.body.vehicle_category || req.body.vehicleCategory || '').toUpperCase();
  const categoryTypes = {
    TWO_WHEELER: 'bike',
    COMPACT_CAR: 'car',
    SUV_SEDAN: 'suv',
    HEAVY_VEHICLE: 'suv',
  };
  const vehicleType = categoryTypes[category] || req.body.vehicleType;
  if (!['bike', 'car', 'suv'].includes(vehicleType)) {
    const error = new Error('Provide a supported vehicle category.');
    error.status = 400;
    throw error;
  }
  res.json({ slot: await recommendSlot(vehicleType) });
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
r.put('/watchlist/:id', wrap(async (req, res) => {
  const updates = {};
  for (const key of ['plate', 'reason', 'active']) {
    if (Object.hasOwn(req.body, key)) updates[key] = req.body[key];
  }
  const entry = await Watchlist.findByIdAndUpdate(
    req.params.id,
    updates,
    { new: true, runValidators: true },
  );
  if (!entry) {
    const error = new Error('Watchlist entry not found.');
    error.status = 404;
    throw error;
  }
  res.json(entry);
}));
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
