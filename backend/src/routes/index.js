import { Router } from 'express';
import ParkingSlot from '../models/ParkingSlot.js';
import ParkingSession from '../models/ParkingSession.js';
import Watchlist from '../models/Watchlist.js';
import Alert from '../models/Alert.js';
import apiKey from '../middleware/apiKey.js';
import { handleEvent } from '../services/events.js';
import { recommendSlot } from '../services/allocation.js';

const r = Router();
const wrap = (fn) => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);

r.get('/health', (req, res) => res.json({ ok: true, time: new Date() }));

// ---- Slots
r.get('/slots', wrap(async (req, res) => res.json(await ParkingSlot.find().sort({ slotId: 1 }))));
r.get('/slots/recommend', wrap(async (req, res) => {
  const slot = await recommendSlot(req.query.type || 'car');
  res.json({ slot });
}));

// ---- Sessions (check-in / check-out history)
r.get('/sessions', wrap(async (req, res) => {
  const filter = req.query.status ? { status: req.query.status } : {};
  res.json(await ParkingSession.find(filter).sort({ createdAt: -1 }).limit(200));
}));

// ---- Watchlist (simulated stolen-vehicle DB)
r.get('/watchlist', wrap(async (req, res) => res.json(await Watchlist.find().sort({ createdAt: -1 }))));
r.post('/watchlist', wrap(async (req, res) => res.status(201).json(await Watchlist.create(req.body))));
r.delete('/watchlist/:id', wrap(async (req, res) => {
  await Watchlist.findByIdAndDelete(req.params.id);
  res.status(204).end();
}));

// ---- Alerts
r.get('/alerts', wrap(async (req, res) => res.json(await Alert.find().sort({ createdAt: -1 }).limit(100))));
r.patch('/alerts/:id/ack', wrap(async (req, res) =>
  res.json(await Alert.findByIdAndUpdate(req.params.id, { acknowledged: true }, { new: true }))));

// ---- Ingestion from the AI service
r.post('/events', apiKey, wrap(async (req, res) => {
  res.status(201).json(await handleEvent(req.app.get('io'), req.body));
}));

export default r;
