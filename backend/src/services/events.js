import ParkingSession from '../models/ParkingSession.js';
import ParkingSlot from '../models/ParkingSlot.js';
import Watchlist from '../models/Watchlist.js';
import Alert from '../models/Alert.js';
import { recommendSlot } from './allocation.js';

async function raiseAlert(io, data) {
  const alert = await Alert.create(data);
  io.emit('alert:new', alert);
  return alert;
}

async function checkWatchlist(io, plate, cameraId, slotId) {
  if (!plate) return;
  const hit = await Watchlist.findOne({ plate, active: true });
  if (hit) {
    await raiseAlert(io, {
      type: 'stolen_vehicle',
      severity: 'high',
      plate,
      cameraId,
      slotId,
      message: `Watchlist match: ${plate} (${hit.reason})`,
    });
  }
}

async function emitSlots(io) {
  io.emit('slots:update', await ParkingSlot.find().sort({ slotId: 1 }));
}

/**
 * Handles one event from the AI service.
 * type: entry | plate | parked | exit | wrong_parking | crash
 */
export async function handleEvent(io, ev) {
  const { type, trackId, cameraId = 'cam-1', plate = null, vehicleType = 'car', slotId = null } = ev;

  switch (type) {
    case 'entry': {
      const rec = await recommendSlot(vehicleType);
      const session = await ParkingSession.create({
        trackId, cameraId, plate, vehicleType,
        entryTime: ev.timestamp ? new Date(ev.timestamp) : new Date(),
      });
      io.emit('session:new', session);
      await checkWatchlist(io, plate, cameraId, null);
      return { session, recommendedSlot: rec ? rec.slotId : null };
    }
    case 'plate': {
      const session = await ParkingSession.findOneAndUpdate(
        { trackId, status: 'active' }, { plate }, { new: true, sort: { createdAt: -1 } }
      );
      await checkWatchlist(io, plate, cameraId, session?.slotId ?? null);
      if (session) io.emit('session:update', session);
      return { session };
    }
    case 'parked': {
      const session = await ParkingSession.findOneAndUpdate(
        { trackId, status: 'active' }, { slotId }, { new: true, sort: { createdAt: -1 } }
      );
      if (slotId) {
        await ParkingSlot.updateOne(
          { slotId }, { status: 'occupied', currentSession: session?._id ?? null }
        );
        await emitSlots(io);
      }
      return { session };
    }
    case 'exit': {
      const session = await ParkingSession.findOne({ trackId, status: 'active' }).sort({ createdAt: -1 });
      if (!session) return { session: null };
      session.exitTime = ev.timestamp ? new Date(ev.timestamp) : new Date();
      session.durationSec = Math.round((session.exitTime - session.entryTime) / 1000);
      session.status = 'closed';
      await session.save();
      if (session.slotId) {
        await ParkingSlot.updateOne({ slotId: session.slotId }, { status: 'free', currentSession: null });
        await emitSlots(io);
      }
      io.emit('session:update', session);
      return { session };
    }
    case 'wrong_parking':
      return { alert: await raiseAlert(io, {
        type: 'wrong_parking', severity: 'medium', plate, cameraId, slotId,
        message: ev.message || 'Vehicle parked outside a valid slot / blocking path',
      }) };
    case 'crash':
      return { alert: await raiseAlert(io, {
        type: 'crash', severity: 'high', plate, cameraId,
        message: ev.message || 'Possible collision detected', snapshot: ev.snapshot || null,
      }) };
    default: {
      const err = new Error(`Unknown event type: ${type}`);
      err.status = 400;
      throw err;
    }
  }
}

// Sprint 5: call on an interval from server.js to flag long stays.
export async function checkOverstays(io) {
  const limitMs = (Number(process.env.OVERSTAY_HOURS) || 4) * 3600 * 1000;
  const cutoff = new Date(Date.now() - limitMs);
  const stale = await ParkingSession.find({
    status: 'active', overstayAlerted: false, entryTime: { $lt: cutoff },
  });
  for (const s of stale) {
    await raiseAlert(io, {
      type: 'overstay', severity: 'low', plate: s.plate, slotId: s.slotId,
      message: `Vehicle exceeded ${process.env.OVERSTAY_HOURS || 4}h`,
    });
    s.overstayAlerted = true;
    await s.save();
  }
}
